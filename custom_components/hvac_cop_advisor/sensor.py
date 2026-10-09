"""Sensor platform for HVAC COP & Thermal Performance Advisor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_COP_EER,
    SENSOR_CUMULATIVE_ELECTRIC_ENERGY,
    SENSOR_CUMULATIVE_THERMAL_ENERGY,
    SENSOR_DAILY_COP,
    SENSOR_MODULATION,
    SENSOR_THERMAL_POWER,
)
from .coordinator import HvacCopAdvisorCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HVAC COP Advisor sensors."""
    coordinator: HvacCopAdvisorCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        HvacCopEerSensor(coordinator),
        HvacThermalPowerSensor(coordinator),
        HvacModulationSensor(coordinator),
        HvacCumulativeElectricSensor(coordinator),
        HvacCumulativeThermalSensor(coordinator),
        HvacDailyCopSensor(coordinator),
    ]

    async_add_entities(entities)


class HvacAdvisorBaseSensor(
    CoordinatorEntity[HvacCopAdvisorCoordinator], SensorEntity
):
    """Base sensor for HVAC COP Advisor entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HvacCopAdvisorCoordinator,
        key: str,
    ) -> None:
        """Initialize the base sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information associating this entity with the HVAC advisor device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.entry.entry_id)},
            name=self.coordinator.device_name,
            manufacturer="HVAC Advisor",
            model="Thermodynamic COP Engine",
            entry_type=DeviceEntryType.SERVICE,
        )


class HvacCopEerSensor(HvacAdvisorBaseSensor):
    """Instantaneous COP / EER Sensor."""

    def __init__(self, coordinator: HvacCopAdvisorCoordinator) -> None:
        """Initialize the COP/EER sensor."""
        super().__init__(coordinator, SENSOR_COP_EER)
        self.entity_description = SensorEntityDescription(
            key=SENSOR_COP_EER,
            translation_key=SENSOR_COP_EER,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:heat-pump-outline",
        )

    @property
    def native_value(self) -> float | None:
        """Return the calculated effective COP or EER."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(SENSOR_COP_EER)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return operating attributes."""
        if not self.coordinator.data:
            return {}
        mode = self.coordinator.data.get("mode", "idle")
        return {
            "mode": mode,
            "metric_type": "COP" if mode == "heat" else "EER" if mode == "cool" else "idle",
            "is_standby": self.coordinator.data.get("is_standby", True),
            "outdoor_temp": self.coordinator.data.get("outdoor_temp"),
            "indoor_temp": self.coordinator.data.get("indoor_temp"),
        }


class HvacThermalPowerSensor(HvacAdvisorBaseSensor):
    """Instantaneous Thermal Power Output Sensor."""

    def __init__(self, coordinator: HvacCopAdvisorCoordinator) -> None:
        """Initialize thermal power sensor."""
        super().__init__(coordinator, SENSOR_THERMAL_POWER)
        self.entity_description = SensorEntityDescription(
            key=SENSOR_THERMAL_POWER,
            translation_key=SENSOR_THERMAL_POWER,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
        )

    @property
    def icon(self) -> str:
        """Return dynamic icon based on heating or cooling mode."""
        if self.coordinator.data:
            mode = self.coordinator.data.get("mode")
            if mode == "heat":
                return "mdi:fire"
            if mode == "cool":
                return "mdi:snowflake"
        return "mdi:heat-pump-outline"

    @property
    def native_value(self) -> float | None:
        """Return instantaneous thermal power output in Watts."""
        if not self.coordinator.data:
            return 0.0
        return self.coordinator.data.get(SENSOR_THERMAL_POWER, 0.0)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional diagnostics."""
        if not self.coordinator.data:
            return {}
        return {
            "electric_power_watts": self.coordinator.data.get("measured_electric_watts"),
            "mode": self.coordinator.data.get("mode"),
        }


class HvacModulationSensor(HvacAdvisorBaseSensor):
    """Compressor Inverter Modulation Sensor."""

    def __init__(self, coordinator: HvacCopAdvisorCoordinator) -> None:
        """Initialize compressor modulation sensor."""
        super().__init__(coordinator, SENSOR_MODULATION)
        self.entity_description = SensorEntityDescription(
            key=SENSOR_MODULATION,
            translation_key=SENSOR_MODULATION,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=PERCENTAGE,
            icon="mdi:gauge",
        )

    @property
    def native_value(self) -> float | None:
        """Return compressor modulation percentage."""
        if not self.coordinator.data:
            return 0.0
        return self.coordinator.data.get(SENSOR_MODULATION, 0.0)


class HvacCumulativeElectricSensor(HvacAdvisorBaseSensor, RestoreEntity):
    """Cumulative Electric Energy Consumed Sensor (kWh, total_increasing)."""

    def __init__(self, coordinator: HvacCopAdvisorCoordinator) -> None:
        """Initialize cumulative electric energy sensor."""
        super().__init__(coordinator, SENSOR_CUMULATIVE_ELECTRIC_ENERGY)
        self.entity_description = SensorEntityDescription(
            key=SENSOR_CUMULATIVE_ELECTRIC_ENERGY,
            translation_key=SENSOR_CUMULATIVE_ELECTRIC_ENERGY,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            icon="mdi:lightning-bolt",
        )

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in ("unknown", "unavailable"):
            try:
                restored_val = float(last_state.state)
                self.coordinator.restore_cumulative_counters(
                    electric_kwh=restored_val, thermal_kwh=None
                )
            except (ValueError, TypeError):
                pass

    @property
    def native_value(self) -> float | None:
        """Return total cumulative electric energy."""
        if not self.coordinator.data:
            return round(self.coordinator.cumulative_electric_kwh, 3)
        return self.coordinator.data.get(
            SENSOR_CUMULATIVE_ELECTRIC_ENERGY,
            round(self.coordinator.cumulative_electric_kwh, 3),
        )


class HvacCumulativeThermalSensor(HvacAdvisorBaseSensor, RestoreEntity):
    """Cumulative Thermal Energy Delivered Sensor (kWh, total_increasing)."""

    def __init__(self, coordinator: HvacCopAdvisorCoordinator) -> None:
        """Initialize cumulative thermal energy sensor."""
        super().__init__(coordinator, SENSOR_CUMULATIVE_THERMAL_ENERGY)
        self.entity_description = SensorEntityDescription(
            key=SENSOR_CUMULATIVE_THERMAL_ENERGY,
            translation_key=SENSOR_CUMULATIVE_THERMAL_ENERGY,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            icon="mdi:chart-bell-curve",
        )

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in ("unknown", "unavailable"):
            try:
                restored_val = float(last_state.state)
                self.coordinator.restore_cumulative_counters(
                    electric_kwh=None, thermal_kwh=restored_val
                )
            except (ValueError, TypeError):
                pass

    @property
    def native_value(self) -> float | None:
        """Return total cumulative thermal energy."""
        if not self.coordinator.data:
            return round(self.coordinator.cumulative_thermal_kwh, 3)
        return self.coordinator.data.get(
            SENSOR_CUMULATIVE_THERMAL_ENERGY,
            round(self.coordinator.cumulative_thermal_kwh, 3),
        )


class HvacDailyCopSensor(HvacAdvisorBaseSensor):
    """Daily Average COP Sensor (SCOP_daily)."""

    def __init__(self, coordinator: HvacCopAdvisorCoordinator) -> None:
        """Initialize daily COP sensor."""
        super().__init__(coordinator, SENSOR_DAILY_COP)
        self.entity_description = SensorEntityDescription(
            key=SENSOR_DAILY_COP,
            translation_key=SENSOR_DAILY_COP,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:chart-timeline-variant",
        )

    @property
    def native_value(self) -> float | None:
        """Return daily average COP."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(SENSOR_DAILY_COP)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return daily energy components."""
        return {
            "daily_electric_kwh": round(self.coordinator.daily_electric_kwh, 3),
            "daily_thermal_kwh": round(self.coordinator.daily_thermal_kwh, 3),
        }
