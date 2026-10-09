"""Binary sensor platform for HVAC COP & Thermal Performance Advisor."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BINARY_SENSOR_HEAT_RECOMMENDED,
    BINARY_SENSOR_PREHEATING_ADVISOR,
    DOMAIN,
)
from .coordinator import HvacCopAdvisorCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HVAC COP Advisor binary sensors."""
    coordinator: HvacCopAdvisorCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = [
        HvacHeatRecommendedSensor(coordinator),
        HvacPreheatingAdvisorSensor(coordinator),
    ]

    async_add_entities(entities)


class HvacAdvisorBaseBinarySensor(
    CoordinatorEntity[HvacCopAdvisorCoordinator], BinarySensorEntity
):
    """Base binary sensor for HVAC COP Advisor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HvacCopAdvisorCoordinator,
        key: str,
    ) -> None:
        """Initialize the base binary sensor."""
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
            manufacturer="pegaverzum",
            model="Thermodynamic COP Engine",
            entry_type=DeviceEntryType.SERVICE,
        )


class HvacHeatRecommendedSensor(HvacAdvisorBaseBinarySensor):
    """Binary sensor indicating if current COP justifies heating."""

    def __init__(self, coordinator: HvacCopAdvisorCoordinator) -> None:
        """Initialize heat recommended binary sensor."""
        super().__init__(coordinator, BINARY_SENSOR_HEAT_RECOMMENDED)
        self.entity_description = BinarySensorEntityDescription(
            key=BINARY_SENSOR_HEAT_RECOMMENDED,
            translation_key=BINARY_SENSOR_HEAT_RECOMMENDED,
            device_class=BinarySensorDeviceClass.HEAT,
        )

    @property
    def is_on(self) -> bool:
        """Return true if heating is thermodynamically viable / recommended."""
        if not self.coordinator.data:
            return False
        rec_data = self.coordinator.data.get(
            BINARY_SENSOR_HEAT_RECOMMENDED, {}
        )
        return bool(rec_data.get("state", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return efficiency rating and current COP."""
        if not self.coordinator.data:
            return {}
        rec_data = self.coordinator.data.get(
            BINARY_SENSOR_HEAT_RECOMMENDED, {}
        )
        return {
            "efficiency_rating": rec_data.get("efficiency_rating", "unknown"),
            "current_cop": rec_data.get("current_cop"),
            "cop_threshold": self.coordinator.cop_threshold,
        }


class HvacPreheatingAdvisorSensor(HvacAdvisorBaseBinarySensor):
    """Binary sensor indicating smart weather pre-heating recommendation."""

    def __init__(self, coordinator: HvacCopAdvisorCoordinator) -> None:
        """Initialize preheating advisor binary sensor."""
        super().__init__(coordinator, BINARY_SENSOR_PREHEATING_ADVISOR)
        self.entity_description = BinarySensorEntityDescription(
            key=BINARY_SENSOR_PREHEATING_ADVISOR,
            translation_key=BINARY_SENSOR_PREHEATING_ADVISOR,
            icon="mdi:weather-sunset-down",
        )

    @property
    def is_on(self) -> bool:
        """Return true if pre-heating is recommended before a weather cold snap."""
        if not self.coordinator.data:
            return False
        advisor_data = self.coordinator.data.get(
            BINARY_SENSOR_PREHEATING_ADVISOR, {}
        )
        return bool(advisor_data.get("state", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return weather forecast drop details and advice."""
        if not self.coordinator.data:
            return {}
        advisor_data = self.coordinator.data.get(
            BINARY_SENSOR_PREHEATING_ADVISOR, {}
        )
        return {
            "forecast_min_temp": advisor_data.get("forecast_min_temp"),
            "temp_drop": advisor_data.get("temp_drop"),
            "recommendation_text": advisor_data.get("recommendation_text", ""),
        }
