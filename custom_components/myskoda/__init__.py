"""The MySkoda integration."""

from __future__ import annotations

import logging

from aiohttp import InvalidUrlClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.util.ssl import get_default_context
from myskoda import (
    MySkoda,
    AuthorizationFailedError,
)
from myskoda.myskoda import TRACE_CONFIG
from myskoda.auth.authorization import CSRFError, TermsAndConditionsError


from .const import COORDINATORS, DOMAIN
from .coordinator import MySkodaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.CLIMATE,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.BINARY_SENSOR,
    Platform.IMAGE,
    Platform.LOCK,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Set up MySkoda integration from a config entry."""

    trace_configs = []
    if config.options.get("tracing"):
        trace_configs.append(TRACE_CONFIG)

    session = async_create_clientsession(
        hass, trace_configs=trace_configs, auto_cleanup=False
    )
    myskoda = MySkoda(session, get_default_context())

    # TODO @webspider: Figure out how to make these show nicely and transatable in UI
    try:
        await myskoda.connect(config.data["email"], config.data["password"])
    except AuthorizationFailedError:
        _LOGGER.debug("Authorization with MySkoda failed.")
        raise ConfigEntryAuthFailed("Authentication failed.")
    except TermsAndConditionsError:
        _LOGGER.error(
            "New terms and conditions detected while logging in. Please log into the MySkoda app (may require a logout first) to access the new Terms and Condidions. This HomeAssistant integration currently can not continue."
        )
        raise TermsAndConditionsError("New Terms and Conditions detected during login")
    except (CSRFError, InvalidUrlClientError):
        _LOGGER.debug("An error occurred during login.")
        raise ConfigEntryNotReady("An error occurred during login.")
    except Exception:
        _LOGGER.exception("Login with MySkoda failed for an unknown reason.")
        return False

    coordinators: dict[str, MySkodaDataUpdateCoordinator] = {}
    vehicles = await myskoda.list_vehicle_vins()
    for vin in vehicles:
        coordinator = MySkodaDataUpdateCoordinator(hass, config, myskoda, vin)
        await coordinator.async_config_entry_first_refresh()
        coordinators[vin] = coordinator

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config.entry_id] = {COORDINATORS: coordinators}

    await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)
    config.async_on_unload(config.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    # Do a lazy reload of integration when configuration changed
    await hass.config_entries.async_reload(entry.entry_id)
