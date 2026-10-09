"""Config flow and Options flow for HVAC COP & Thermal Performance Advisor."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)

from .const import (
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
    DEFAULT_COP_THRESHOLD,
    DEFAULT_K_COP,
    DEFAULT_K_EER,
    DEFAULT_NAME,
    DEFAULT_NOMINAL_CAPACITY_KW,
    DEFAULT_NOMINAL_COP,
    DEFAULT_NOMINAL_EER,
    DEFAULT_STANDBY_THRESHOLD,
    DOMAIN,
)


class HvacCopAdvisorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HVAC COP & Thermal Performance Advisor."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial user setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check for unique identifier based on climate entity
            unique_id = f"{DOMAIN}_{user_input[CONF_CLIMATE_ENTITY]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            title = user_input.get(CONF_NAME, DEFAULT_NAME)
            return self.async_create_entry(title=title, data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): TextSelector(),
                vol.Required(CONF_CLIMATE_ENTITY): EntitySelector(
                    EntitySelectorConfig(domain="climate")
                ),
                vol.Required(CONF_POWER_SENSOR): EntitySelector(
                    EntitySelectorConfig(
                        domain="sensor",
                        device_class=SensorDeviceClass.POWER,
                    )
                ),
                vol.Required(CONF_OUTDOOR_TEMP_SENSOR): EntitySelector(
                    EntitySelectorConfig(
                        domain="sensor",
                        device_class=SensorDeviceClass.TEMPERATURE,
                    )
                ),
                vol.Required(CONF_INDOOR_TEMP_SENSOR): EntitySelector(
                    EntitySelectorConfig(
                        domain="sensor",
                        device_class=SensorDeviceClass.TEMPERATURE,
                    )
                ),
                vol.Optional(CONF_WEATHER_ENTITY): EntitySelector(
                    EntitySelectorConfig(domain="weather")
                ),
                vol.Required(
                    CONF_NOMINAL_CAPACITY_KW,
                    default=DEFAULT_NOMINAL_CAPACITY_KW,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1.0,
                        max=20.0,
                        step=0.1,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_NOMINAL_COP,
                    default=DEFAULT_NOMINAL_COP,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=2.0,
                        max=6.0,
                        step=0.05,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_NOMINAL_EER,
                    default=DEFAULT_NOMINAL_EER,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=2.0,
                        max=6.0,
                        step=0.05,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return HvacCopAdvisorOptionsFlowHandler(config_entry)


class HvacCopAdvisorOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for HVAC COP Advisor."""

    def __init__(self, config_entry: config_entries.ConfigEntry | None = None) -> None:
        """Initialize options flow."""
        if config_entry is not None:
            try:
                self.config_entry = config_entry
            except AttributeError:
                pass

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry_data = self.config_entry.data
        entry_options = self.config_entry.options

        def get_val(key: str, default: Any) -> Any:
            return entry_options.get(key, entry_data.get(key, default))

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_NOMINAL_CAPACITY_KW,
                    default=float(
                        get_val(
                            CONF_NOMINAL_CAPACITY_KW,
                            DEFAULT_NOMINAL_CAPACITY_KW,
                        )
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1.0,
                        max=20.0,
                        step=0.1,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_NOMINAL_COP,
                    default=float(
                        get_val(CONF_NOMINAL_COP, DEFAULT_NOMINAL_COP)
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=2.0,
                        max=6.0,
                        step=0.05,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_NOMINAL_EER,
                    default=float(
                        get_val(CONF_NOMINAL_EER, DEFAULT_NOMINAL_EER)
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=2.0,
                        max=6.0,
                        step=0.05,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_K_COP,
                    default=float(get_val(CONF_K_COP, DEFAULT_K_COP)),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.01,
                        max=0.20,
                        step=0.005,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_K_EER,
                    default=float(get_val(CONF_K_EER, DEFAULT_K_EER)),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.01,
                        max=0.20,
                        step=0.005,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_STANDBY_THRESHOLD,
                    default=float(
                        get_val(
                            CONF_STANDBY_THRESHOLD, DEFAULT_STANDBY_THRESHOLD
                        )
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0.0,
                        max=100.0,
                        step=1.0,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_COP_THRESHOLD,
                    default=float(
                        get_val(CONF_COP_THRESHOLD, DEFAULT_COP_THRESHOLD)
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1.5,
                        max=5.0,
                        step=0.1,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_WEATHER_ENTITY,
                    description={"suggested_value": get_val(CONF_WEATHER_ENTITY, None)},
                ): EntitySelector(EntitySelectorConfig(domain="weather")),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
