"""Constants for Solar Floor Boost."""

DOMAIN = "solar_floor_boost"

CONF_CLIMATES = "climate_entities"
CONF_MAX_TEMPERATURE = "max_temperature"

DEFAULT_DELTA = 1.0  # °C
DEFAULT_DURATION = 120  # minutes
DEFAULT_MAX_TEMPERATURE = 28.0  # °C, safety cap for any boosted target
DEFAULT_TEMP_STEP = 0.5

ATTR_DELTA = "delta"
ATTR_DURATION = "duration"
ATTR_CLIMATE_ENTITIES = "climate_entities"

SERVICE_START = "start"
SERVICE_STOP = "stop"

STORAGE_VERSION = 1
