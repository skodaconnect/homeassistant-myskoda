"""The MySkoda integration."""

from __future__ import annotations

import logging

from aiohttp import ClientResponseError, InvalidUrlClientError

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
from myskoda.auth.authorization import (
    CSRFError,
    TermsAndConditionsError,
    MarketingConsentError,
)


from .const import COORDINATORS, DOMAIN
from .coordinator import MySkodaDataUpdateCoordinator
from .error_handlers import handle_aiohttp_error
from .issues import (
    async_create_tnc_issue,
    async_delete_tnc_issue,
    async_delete_spin_issue,
)

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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MySkoda integration from a config entry."""

    trace_configs = []
    if entry.options.get("tracing"):
        trace_configs.append(TRACE_CONFIG)

    session = async_create_clientsession(
        hass, trace_configs=trace_configs, auto_cleanup=False
    )
    myskoda = MySkoda(session, get_default_context(), mqtt_enabled=False)

    try:
        await myskoda.connect(entry.data["email"], entry.data["password"])
    except AuthorizationFailedError as exc:
        _LOGGER.debug("Authorization with MySkoda failed.")
        raise ConfigEntryAuthFailed from exc
    except (TermsAndConditionsError, MarketingConsentError) as exc:
        _LOGGER.error(
            "Change to terms and conditions or consents detected while logging in. Please log into the MySkoda app (may require a logout first) to access the new Terms and Conditions. This HomeAssistant integration currently can not continue."
        )
        async_create_tnc_issue(hass, entry.entry_id)
        raise ConfigEntryNotReady from exc
    except (CSRFError, InvalidUrlClientError) as exc:
        _LOGGER.debug("An error occurred during login.")
        raise ConfigEntryNotReady from exc
    except ClientResponseError as err:
        handle_aiohttp_error("setup", err, hass, entry)
    except Exception:
        _LOGGER.exception("Login with MySkoda failed for an unknown reason.")
        return False

    async_delete_tnc_issue(hass, entry.entry_id)
    async_delete_spin_issue(hass, entry.entry_id)

    coordinators: dict[str, MySkodaDataUpdateCoordinator] = {}
    vehicles = await myskoda.list_vehicle_vins()
    for vin in vehicles:
        coordinator = MySkodaDataUpdateCoordinator(hass, entry, myskoda, vin)
        await coordinator.async_config_entry_first_refresh()
        coordinators[vin] = coordinator

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {COORDINATORS: coordinators}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

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
