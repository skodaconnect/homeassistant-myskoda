"""Constants for the MySkoda integration."""

DOMAIN = "myskoda"
COORDINATORS = "coordinators"

DEFAULT_FETCH_INTERVAL_IN_MINUTES = 30  # Default polling interval in minutes
DEFAULT_FETCH_INTERVAL_IN_MINUTES = 30
API_COOLDOWN_IN_SECONDS = 30.0

CONF_POLL_INTERVAL = "poll_interval"  # Changed to a more generic name
CONF_POLL_INTERVAL = "poll_interval_in_minutes"
CONF_POLL_INTERVAL_MIN = 1
CONF_POLL_INTERVAL_MAX = 1440
