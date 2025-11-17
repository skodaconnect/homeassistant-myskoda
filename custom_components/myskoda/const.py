"""Constants for the MySkoda integration."""

DOMAIN = "myskoda"
COORDINATORS = "coordinators"

# Timing information
DEFAULT_FETCH_INTERVAL_IN_MINUTES = 30
API_COOLDOWN_IN_SECONDS = 30.0
MQTT_RECONNECT_INTERVAL_IN_SECONDS = 300

# Configuration information
CONF_USERNAME = "email"
CONF_PASSWORD = "password"
CONF_POLL_INTERVAL = "poll_interval_in_minutes"
CONF_POLL_INTERVAL_MIN = 1
CONF_POLL_INTERVAL_MAX = 1440
CONF_SPIN = "s-pin"
CONF_READONLY = "readonly"
CONF_TRACING = "tracing"
CONF_VINLIST = "vins"

# Queue sizes
MAX_STORED_OPERATIONS = 2
MAX_STORED_SERVICE_EVENTS = 2

# Santiy boundaries
OUTSIDE_TEMP_MIN_BOUND = -50
OUTSIDE_TEMP_MAX_BOUND = 60
