"""The MySkoda integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.util.ssl import get_default_context
from myskoda import MySkoda
from myskoda.myskoda import TRACE_CONFIG
from myskoda.auth.authorization import AuthorizationFailedError

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
]


async def async_connect_myskoda(
    hass: HomeAssistant, entry: ConfigEntry, mqtt_enabled: bool = True
) -> MySkoda:
    """Connect to MySkoda."""

    trace_configs = []
    if entry.options.get("tracing"):
        trace_configs.append(TRACE_CONFIG)

    session = async_create_clientsession(hass, trace_configs=trace_configs)
    myskoda = MySkoda(session, get_default_context(), mqtt_enabled=mqtt_enabled)
    await myskoda.connect(entry.data["email"], entry.data["password"])
    return myskoda


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MySkoda integration from a config entry."""

    try:
        myskoda = await async_connect_myskoda(hass, entry)
    except AuthorizationFailedError as exc:
        raise ConfigEntryAuthFailed("Log in failed for %s: %s", DOMAIN, exc)
    except Exception as exc:
        _LOGGER.exception(
            "Login with %s failed for unknown reason. Details: %s", DOMAIN, exc
        )
        return False

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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle config entry schema migration."""
    _LOGGER.debug(
        "Migrating configuration entry %s from v%s.%s",
        entry.entry_id,
        entry.version,
        entry.minor_version,
    )

    if entry.version > 2:
        return False

    if entry.version == 1:
        # v1 could have a missing unique_id. Bump to 2.1
        if not entry.unique_id or entry.unique_id == "":
            _LOGGER.debug("Starting migration of unique_id")

            new_version = 2
            new_minor_version = 1
            try:
                myskoda = await async_connect_myskoda(hass, entry, mqtt_enabled=False)
                user = await myskoda.get_user()
                unique_id = user.id
            except AuthorizationFailedError as exc:
                raise ConfigEntryAuthFailed("Log in failed for %s: %s", DOMAIN, exc)
            except Exception as exc:
                _LOGGER.exception(
                    "Login with %s failed for unknown reason. Details: %s", DOMAIN, exc
                )
                return False
            _LOGGER.debug("Add unique_id %s to entry %s", unique_id, entry.entry_id)
            hass.config_entries.async_update_entry(
                entry,
                version=new_version,
                minor_version=new_minor_version,
                unique_id=unique_id,
            )

    if new_entry := hass.config_entries.async_get_entry(entry_id=entry.entry_id):
        _LOGGER.debug(
            "Migration of %s to v%s.%s successful",
            entry.entry_id,
            new_entry.version,
            new_entry.minor_version,
        )

    return True
