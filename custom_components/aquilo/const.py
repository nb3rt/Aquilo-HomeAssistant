"""Constants for the Aquilo integration."""

from __future__ import annotations

DOMAIN = "aquilo"

MANUFACTURER = "Aquilo"
MODEL = "Aquilo level sensor"

# The device refreshes its own readings on its own schedule, so polling it
# more often than every few minutes gains nothing. Default to 15 minutes.
DEFAULT_SCAN_INTERVAL = 900  # seconds
MIN_SCAN_INTERVAL = 60  # seconds

REQUEST_TIMEOUT = 10  # seconds

# Options for the alert binary sensors and per-sensor exclusion.
CONF_STALE_HOURS = "stale_hours"
CONF_OVERFLOW_PCT = "overflow_pct"
CONF_EXCLUDED_SENSORS = "excluded_sensors"

# A sensor that has not reported for a day usually has a flat battery or lost
# its radio link; nothing else in the payload says so.
DEFAULT_STALE_HOURS = 24
DEFAULT_OVERFLOW_PCT = 90
