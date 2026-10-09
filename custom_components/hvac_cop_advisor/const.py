"""Constants for the HVAC COP & Thermal Performance Advisor integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "hvac_cop_advisor"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

# Configuration Keys
CONF_NAME = "name"
CONF_CLIMATE_ENTITY = "climate_entity"
CONF_POWER_SENSOR = "power_sensor"
CONF_OUTDOOR_TEMP_SENSOR = "outdoor_temp_sensor"
CONF_INDOOR_TEMP_SENSOR = "indoor_temp_sensor"
CONF_WEATHER_ENTITY = "weather_entity"
CONF_NOMINAL_CAPACITY_KW = "nominal_capacity_kw"
CONF_NOMINAL_COP = "nominal_cop"
CONF_NOMINAL_EER = "nominal_eer"
CONF_K_COP = "k_cop"
CONF_K_EER = "k_eer"
CONF_STANDBY_THRESHOLD = "standby_threshold"
CONF_COP_THRESHOLD = "cop_threshold"

# Default values
DEFAULT_NAME = "Living Room AC"
DEFAULT_NOMINAL_CAPACITY_KW = 3.5
DEFAULT_NOMINAL_COP = 3.8
DEFAULT_NOMINAL_EER = 3.2
DEFAULT_K_COP = 0.065
DEFAULT_K_EER = 0.08
DEFAULT_STANDBY_THRESHOLD = 15.0
DEFAULT_COP_THRESHOLD = 2.8

# Physical & Thermodynamic boundaries
COP_MIN = 1.1
COP_MAX = 6.0
EER_MIN = 1.5
EER_MAX = 6.5

# Reference conditions
TEMP_HEATING_OUTDOOR_REF = 7.0
TEMP_HEATING_INDOOR_REF = 20.0
DELTA_T_HEATING_REF = TEMP_HEATING_INDOOR_REF - TEMP_HEATING_OUTDOOR_REF  # 13.0 C

TEMP_COOLING_OUTDOOR_REF = 35.0
TEMP_COOLING_INDOOR_REF = 27.0

# Pre-heating advisor thresholds
PREHEAT_MIN_OUTDOOR_TEMP = 5.0
PREHEAT_MIN_COP = 3.5
PREHEAT_TEMP_DROP_THRESHOLD = 6.0
PREHEAT_FREEZING_THRESHOLD = -2.0
FORECAST_LOOKAHEAD_HOURS = 12

# Sensor keys
SENSOR_COP_EER = "cop_eer"
SENSOR_THERMAL_POWER = "thermal_power"
SENSOR_MODULATION = "modulation"
SENSOR_CUMULATIVE_ELECTRIC_ENERGY = "cumulative_electric_energy"
SENSOR_CUMULATIVE_THERMAL_ENERGY = "cumulative_thermal_energy"
SENSOR_DAILY_COP = "daily_cop"

# Binary sensor keys
BINARY_SENSOR_HEAT_RECOMMENDED = "heat_recommended"
BINARY_SENSOR_PREHEATING_ADVISOR = "preheating_advisor"
