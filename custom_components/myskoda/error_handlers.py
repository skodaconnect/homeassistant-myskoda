"""Central error handling for HomeAssistant MySkoda integration."""

import logging

from aiohttp import ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from .issues import (
    async_create_spin_issue,
)


_LOGGER = logging.getLogger(__name__)


def handle_aiohttp_error(
    poll_type: str,
    e: ClientResponseError,
    hass: HomeAssistant,
    config: ConfigEntry,
) -> None:
    _LOGGER.debug("Received error %d with content %s", e.status, e.message)

    if e.status == 412:
        # Handle precondition failed by creating an issue for incorrect S-PIN
        async_create_spin_issue(hass, config.entry_id)
        return

    elif e.status in [429, 500]:
        # Log message for error otherwise ignore
        _LOGGER.warning(
            f"Error requesting {poll_type} from MySkoda API: {e.message} ({e.status}), ignoring this"
        )
        return
    else:
        raise UpdateFailed(
            f"Error requesting {poll_type} from MySkoda API: {e.message} ({e.status})"
        )
