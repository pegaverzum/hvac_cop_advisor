"""DataUpdateCoordinator for HVAC COP & Thermal Performance Advisor."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    BINARY_SENSOR_HEAT_RECOMMENDED,
    BINARY_SENSOR_PREHEATING_ADVISOR,
    CONF_CLIMATE_ENTITY,
    CONF_COP_THRESHOLD,
    CONF_INDOOR_TEMP_SENSOR,
    CONF_K_COP,
    CONF_K_EER,
    CONF_NAME,
    CONF_NOMINAL_CAPACITY_KW,
    CONF_NOMINAL_COP,
    CONF_NOMINAL_EER,
    CONF_OUTDOOR_TEMP_SENSOR,
    CONF_POWER_SENSOR,
    CONF_STANDBY_THRESHOLD,
    CONF_WEATHER_ENTITY,
    COP_MAX,
    COP_MIN,
    DEFAULT_COP_THRESHOLD,
    DEFAULT_K_COP,
    DEFAULT_K_EER,
    DEFAULT_NAME,
    DEFAULT_NOMINAL_CAPACITY_KW,
    DEFAULT_NOMINAL_COP,
    DEFAULT_NOMINAL_EER,
    DEFAULT_STANDBY_THRESHOLD,
    DELTA_T_HEATING_REF,
    DOMAIN,
    EER_MAX,
    EER_MIN,
    FORECAST_LOOKAHEAD_HOURS,
    PREHEAT_FREEZING_THRESHOLD,
    PREHEAT_MIN_COP,
    PREHEAT_MIN_OUTDOOR_TEMP,
    PREHEAT_TEMP_DROP_THRESHOLD,
    SENSOR_COP_EER,
    SENSOR_CUMULATIVE_ELECTRIC_ENERGY,
    SENSOR_CUMULATIVE_THERMAL_ENERGY,
    SENSOR_DAILY_COP,
    SENSOR_MODULATION,
    SENSOR_THERMAL_POWER,
    TEMP_COOLING_OUTDOOR_REF,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)
FORECAST_INTERVAL = timedelta(minutes=15)


def calculate_partial_load_multiplier(modulation: float) -> float:
    """Calculate the thermodynamic partial load efficiency multiplier.

    - Optimal partial load (30% to 65%): boost up to +12% at 47.5%.
    - Low load (<30%): smooth transition from 1.0 to 1.08.
    - Medium-high load (65% to 80%): smooth transition from 1.12 to 1.0.
    - Nominal load (80% to 100%): 1.0.
    - Overdrive (>100% to 150%): penalty up to -20%.
    """
    if 30.0 <= modulation <= 65.0:
        return 1.0 + 0.12 * (1.0 - abs((modulation - 47.5) / 17.5))
    if modulation < 30.0:
        return 1.0 + (modulation / 30.0) * (0.12 * (1.0 - abs((30.0 - 47.5) / 17.5)))
    if 65.0 < modulation <= 80.0:
        peak_at_65 = 1.0 + 0.12 * (1.0 - abs((65.0 - 47.5) / 17.5))
        ratio = (80.0 - modulation) / 15.0
        return 1.0 + ratio * (peak_at_65 - 1.0)
    if 80.0 < modulation <= 100.0:
        return 1.0
    # Overdrive > 100%
    penalty = min(0.25, ((modulation - 100.0) / 50.0) * 0.20)
    return max(0.75, 1.0 - penalty)


class HvacCopAdvisorCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching and calculating HVAC COP & thermal data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self._unsub_listeners: list[callback] = []

        # Cumulative counters
        self.cumulative_electric_kwh: float = 0.0
        self.cumulative_thermal_kwh: float = 0.0
        self.daily_electric_kwh: float = 0.0
        self.daily_thermal_kwh: float = 0.0

        # State tracking for integration
        self._last_integration_time: datetime | dt_util.dt.datetime | None = None
        self._last_electric_watts: float = 0.0
        self._last_thermal_watts: float = 0.0
        self._last_date: datetime.date | None = None

        # Weather forecast cache
        self._last_forecast_time: datetime | None = None
        self._forecast_data: list[dict[str, Any]] = []

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=UPDATE_INTERVAL,
        )

    @property
    def name(self) -> str:
        """Return the device name configured by the user."""
        return self.entry.data.get(CONF_NAME, DEFAULT_NAME)

    @property
    def climate_entity(self) -> str:
        """Return the target climate entity ID."""
        return self.entry.data.get(CONF_CLIMATE_ENTITY, "")

    @property
    def power_sensor(self) -> str:
        """Return the power sensor entity ID."""
        return self.entry.data.get(CONF_POWER_SENSOR, "")

    @property
    def outdoor_temp_sensor(self) -> str:
        """Return the outdoor temperature sensor entity ID."""
        return self.entry.data.get(CONF_OUTDOOR_TEMP_SENSOR, "")

    @property
    def indoor_temp_sensor(self) -> str:
        """Return the indoor temperature sensor entity ID."""
        return self.entry.data.get(CONF_INDOOR_TEMP_SENSOR, "")

    @property
    def weather_entity(self) -> str | None:
        """Return the weather entity ID if configured."""
        return self.entry.options.get(
            CONF_WEATHER_ENTITY, self.entry.data.get(CONF_WEATHER_ENTITY)
        )

    @property
    def nominal_capacity_kw(self) -> float:
        """Return the nominal heating/cooling capacity in kW."""
        return float(
            self.entry.options.get(
                CONF_NOMINAL_CAPACITY_KW,
                self.entry.data.get(
                    CONF_NOMINAL_CAPACITY_KW, DEFAULT_NOMINAL_CAPACITY_KW
                ),
            )
        )

    @property
    def nominal_cop(self) -> float:
        """Return nominal heating COP."""
        return float(
            self.entry.options.get(
                CONF_NOMINAL_COP,
                self.entry.data.get(CONF_NOMINAL_COP, DEFAULT_NOMINAL_COP),
            )
        )

    @property
    def nominal_eer(self) -> float:
        """Return nominal cooling EER."""
        return float(
            self.entry.options.get(
                CONF_NOMINAL_EER,
                self.entry.data.get(CONF_NOMINAL_EER, DEFAULT_NOMINAL_EER),
            )
        )

    @property
    def k_cop(self) -> float:
        """Return the heating COP slope coefficient."""
        return float(
            self.entry.options.get(
                CONF_K_COP, self.entry.data.get(CONF_K_COP, DEFAULT_K_COP)
            )
        )

    @property
    def k_eer(self) -> float:
        """Return the cooling EER slope coefficient."""
        return float(
            self.entry.options.get(
                CONF_K_EER, self.entry.data.get(CONF_K_EER, DEFAULT_K_EER)
            )
        )

    @property
    def standby_threshold(self) -> float:
        """Return the standby power threshold in Watts."""
        return float(
            self.entry.options.get(
                CONF_STANDBY_THRESHOLD,
                self.entry.data.get(
                    CONF_STANDBY_THRESHOLD, DEFAULT_STANDBY_THRESHOLD
                ),
            )
        )

    @property
    def cop_threshold(self) -> float:
        """Return the COP threshold for the heat recommendation sensor."""
        return float(
            self.entry.options.get(
                CONF_COP_THRESHOLD,
                self.entry.data.get(CONF_COP_THRESHOLD, DEFAULT_COP_THRESHOLD),
            )
        )

    def restore_cumulative_counters(
        self, electric_kwh: float | None, thermal_kwh: float | None
    ) -> None:
        """Restore saved cumulative energy values after HA restart."""
        if electric_kwh is not None and electric_kwh >= self.cumulative_electric_kwh:
            self.cumulative_electric_kwh = electric_kwh
            _LOGGER.debug(
                "Restored cumulative electric energy: %.3f kWh", electric_kwh
            )
        if thermal_kwh is not None and thermal_kwh >= self.cumulative_thermal_kwh:
            self.cumulative_thermal_kwh = thermal_kwh
            _LOGGER.debug(
                "Restored cumulative thermal energy: %.3f kWh", thermal_kwh
            )

    async def async_setup(self) -> None:
        """Set up listeners and initial data."""
        tracked_entities = [
            entity
            for entity in [
                self.climate_entity,
                self.power_sensor,
                self.outdoor_temp_sensor,
                self.indoor_temp_sensor,
            ]
            if entity
        ]

        @callback
        def _async_state_changed_listener(
            event: Event[EventStateChangedData],
        ) -> None:
            """Handle state changes on watched entities."""
            self.hass.async_create_task(self.async_refresh())

        if tracked_entities:
            unsub = async_track_state_change_event(
                self.hass, tracked_entities, _async_state_changed_listener
            )
            self._unsub_listeners.append(unsub)

    def async_unload(self) -> None:
        """Unsubscribe all listeners."""
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

    def _safe_float(self, entity_id: str | None) -> float | None:
        """Safely extract a float value from a Home Assistant entity state."""
        if not entity_id:
            return None
        state_obj = self.hass.states.get(entity_id)
        if state_obj is None or state_obj.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state_obj.state)
        except (ValueError, TypeError):
            return None

    def _get_climate_state(self) -> str | None:
        """Extract the climate entity's current state."""
        if not self.climate_entity:
            return None
        state_obj = self.hass.states.get(self.climate_entity)
        if state_obj is None or state_obj.state in ("unknown", "unavailable"):
            return None
        return state_obj.state

    async def _async_fetch_weather_forecasts(self) -> list[dict[str, Any]]:
        """Fetch hourly weather forecasts via the modern HA service or fallback."""
        if not self.weather_entity:
            return []

        now = dt_util.now()
        if (
            self._last_forecast_time
            and (now - self._last_forecast_time) < FORECAST_INTERVAL
            and self._forecast_data
        ):
            return self._forecast_data

        forecasts: list[dict[str, Any]] = []

        # 1. Try modern weather.get_forecasts action / service
        try:
            response = await self.hass.services.async_call(
                "weather",
                "get_forecasts",
                {"entity_id": self.weather_entity, "type": "hourly"},
                blocking=True,
                return_response=True,
            )
            if response and self.weather_entity in response:
                forecasts = response[self.weather_entity].get("forecast") or []
        except Exception as err:
            _LOGGER.debug(
                "weather.get_forecasts service call failed or not supported: %s. Trying state attributes fallback.",
                err,
            )

        # 2. Fallback to state attributes for older HA versions
        if not forecasts:
            state_obj = self.hass.states.get(self.weather_entity)
            if state_obj and "forecast" in state_obj.attributes:
                forecasts = state_obj.attributes.get("forecast") or []

        self._forecast_data = forecasts
        self._last_forecast_time = now
        return forecasts

    async def _async_update_data(self) -> dict[str, Any]:
        """Perform calculations for COP, EER, thermal power, and energy accumulation."""
        now = dt_util.now()
        current_date = now.date()

        # Handle daily reset at midnight
        if self._last_date is not None and self._last_date != current_date:
            _LOGGER.debug("Day rollover detected. Resetting daily energy accumulators.")
            self.daily_electric_kwh = 0.0
            self.daily_thermal_kwh = 0.0
        self._last_date = current_date

        climate_state = self._get_climate_state()
        p_electric = self._safe_float(self.power_sensor)
        t_outdoor = self._safe_float(self.outdoor_temp_sensor)
        t_indoor = self._safe_float(self.indoor_temp_sensor)

        is_heating = climate_state == HVACMode.HEAT
        is_cooling = climate_state == HVACMode.COOL
        is_active_mode = is_heating or is_cooling

        standby_limit = self.standby_threshold
        is_standby = (
            not is_active_mode
            or p_electric is None
            or p_electric < standby_limit
        )

        cop_effective: float | None = None
        thermal_watts: float = 0.0
        modulation: float = 0.0
        mode_type = "heat" if is_heating else "cool" if is_cooling else "idle"

        if not is_standby and p_electric is not None:
            # 1. Base temperature-dependent COP/EER calculation
            if is_heating:
                t_in = t_indoor if t_indoor is not None else 20.0
                t_out = t_outdoor if t_outdoor is not None else 7.0
                delta_t = t_in - t_out
                base_cop = self.nominal_cop - self.k_cop * (
                    delta_t - DELTA_T_HEATING_REF
                )
                base_cop = max(COP_MIN, min(COP_MAX, base_cop))
                nom_power_w = (
                    self.nominal_capacity_kw * 1000.0
                ) / self.nominal_cop
            else:  # is_cooling
                t_out = t_outdoor if t_outdoor is not None else 35.0
                base_eer = self.nominal_eer - self.k_eer * (
                    t_out - TEMP_COOLING_OUTDOOR_REF
                )
                base_cop = max(EER_MIN, min(EER_MAX, base_eer))
                nom_power_w = (
                    self.nominal_capacity_kw * 1000.0
                ) / self.nominal_eer

            # 2. Compressor modulation calculation
            if nom_power_w > 0:
                modulation = min(
                    150.0, max(0.0, (p_electric / nom_power_w) * 100.0)
                )

            # 3. Partial-load thermodynamic efficiency modifier
            multiplier = calculate_partial_load_multiplier(modulation)
            cop_effective = round(base_cop * multiplier, 2)

            # 4. Instantaneous Thermal Power Output
            thermal_watts = round(p_electric * cop_effective, 1)

        # 5. Energy Integration (Riemann Trapezoidal Sum)
        curr_elec_watts = p_electric if (not is_standby and p_electric is not None) else 0.0
        curr_therm_watts = thermal_watts

        if self._last_integration_time is not None:
            time_delta_sec = (now - self._last_integration_time).total_seconds()
            # Bound integration window to prevent unrealistic jumps if HA was paused
            if 0 < time_delta_sec <= 300:
                avg_elec_w = (self._last_electric_watts + curr_elec_watts) / 2.0
                avg_therm_w = (self._last_thermal_watts + curr_therm_watts) / 2.0

                delta_elec_kwh = (avg_elec_w * time_delta_sec) / 3600000.0
                delta_therm_kwh = (avg_therm_w * time_delta_sec) / 3600000.0

                self.cumulative_electric_kwh += delta_elec_kwh
                self.cumulative_thermal_kwh += delta_therm_kwh
                self.daily_electric_kwh += delta_elec_kwh
                self.daily_thermal_kwh += delta_therm_kwh

        self._last_integration_time = now
        self._last_electric_watts = curr_elec_watts
        self._last_thermal_watts = curr_therm_watts

        # 6. Daily Average COP
        daily_cop: float | None = None
        if self.daily_electric_kwh > 0.02:
            daily_cop = round(
                self.daily_thermal_kwh / self.daily_electric_kwh, 2
            )

        # 7. Heating recommendation
        heat_recommended = (
            cop_effective is not None
            and cop_effective >= self.cop_threshold
        )
        if cop_effective is not None:
            if cop_effective >= 3.8:
                efficiency_rating = "excellent"
            elif cop_effective >= self.cop_threshold:
                efficiency_rating = "acceptable"
            else:
                efficiency_rating = "poor"
        else:
            efficiency_rating = "idle"

        # 8. Weather Pre-heating Advisor
        forecasts = await self._async_fetch_weather_forecasts()
        preheating_advisor = False
        forecast_min_temp: float | None = None
        temp_drop: float | None = None
        preheat_reason = ""

        if forecasts and t_outdoor is not None:
            # Check forecasts within lookahead hours
            temps: list[float] = []
            for item in forecasts[:FORECAST_LOOKAHEAD_HOURS]:
                temp_val = item.get("temperature")
                if temp_val is not None:
                    try:
                        temps.append(float(temp_val))
                    except (ValueError, TypeError):
                        pass

            if temps:
                forecast_min_temp = min(temps)
                temp_drop = round(t_outdoor - forecast_min_temp, 1)

                if (
                    is_heating
                    and not is_standby
                    and t_outdoor >= PREHEAT_MIN_OUTDOOR_TEMP
                    and cop_effective is not None
                    and cop_effective >= PREHEAT_MIN_COP
                ):
                    if (
                        temp_drop >= PREHEAT_TEMP_DROP_THRESHOLD
                        or forecast_min_temp <= PREHEAT_FREEZING_THRESHOLD
                    ):
                        preheating_advisor = True
                        preheat_reason = (
                            f"Favorable outdoor temp ({t_outdoor}°C, COP {cop_effective}) "
                            f"before upcoming drop to {forecast_min_temp}°C (ΔT {temp_drop}°C). "
                            "Pre-heating building thermal mass now saves energy."
                        )

        return {
            SENSOR_COP_EER: cop_effective,
            SENSOR_THERMAL_POWER: thermal_watts,
            SENSOR_MODULATION: round(modulation, 1) if not is_standby else 0.0,
            SENSOR_CUMULATIVE_ELECTRIC_ENERGY: round(
                self.cumulative_electric_kwh, 3
            ),
            SENSOR_CUMULATIVE_THERMAL_ENERGY: round(
                self.cumulative_thermal_kwh, 3
            ),
            SENSOR_DAILY_COP: daily_cop,
            BINARY_SENSOR_HEAT_RECOMMENDED: {
                "state": heat_recommended,
                "efficiency_rating": efficiency_rating,
                "current_cop": cop_effective,
            },
            BINARY_SENSOR_PREHEATING_ADVISOR: {
                "state": preheating_advisor,
                "forecast_min_temp": forecast_min_temp,
                "temp_drop": temp_drop,
                "recommendation_text": preheat_reason,
            },
            "mode": mode_type,
            "is_standby": is_standby,
            "measured_electric_watts": p_electric,
            "outdoor_temp": t_outdoor,
            "indoor_temp": t_indoor,
        }
