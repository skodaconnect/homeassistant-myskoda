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


from .const import COORDINATORS, DOMAIN, VINLIST
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


def myskoda_instantiate(
    hass: HomeAssistant, entry: ConfigEntry, mqtt_enabled: bool = True
) -> MySkoda:
    """Generic connector to MySkoda REST API."""

    trace_configs = []
    if entry.options.get("tracing"):
        trace_configs.append(TRACE_CONFIG)

    session = async_create_clientsession(
        hass, trace_configs=trace_configs, auto_cleanup=False
    )
    return MySkoda(session, get_default_context(), mqtt_enabled=mqtt_enabled)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MySkoda integration from a config entry."""

    myskoda = myskoda_instantiate(hass, entry, mqtt_enabled=False)

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
    cached_vins: list = entry.data.get(VINLIST, [])

    try:
        vehicles = await myskoda.list_vehicle_vins()
        if vehicles and vehicles != cached_vins:
            _LOGGER.info("New vehicles detected. Storing new vehicle list in cache")
            entry_data = {**entry.data}
            entry_data[VINLIST] = vehicles
            hass.config_entries.async_update_entry(entry, data=entry_data)
    except Exception:
        if cached_vins:
            vehicles = cached_vins
            _LOGGER.warning(
                "Using cached list of VINs. This will work only if there is a temporary issue with MySkoda API"
            )
            pass
        else:
            raise

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
    """Handle MySkoda config-entry schema migrations."""

    _LOGGER.debug(
        "Migrating config entry %s from v%s.%s",
        entry.entry_id,
        entry.version,
        entry.minor_version,
    )

    # Only handle known versions. Bump this if you introduce a new major version.
    # We use the following version scheme:
    # - Minor increase: Adding new options
    # - Major increase: Removing options or rewriting entities/devices
    if entry.version > 2:
        _LOGGER.error(
            "Configuration for %s is too new. This can happen if you downgraded your HA install. Automatic configuration migration aborted.",
            DOMAIN,
        )
        return False

    # We will likely need to contact myskoda, so make a connection and authenticate
    try:
        myskoda = myskoda_instantiate(hass, entry, mqtt_enabled=False)
        await myskoda.connect(entry.data["email"], entry.data["password"])
    except AuthorizationFailedError as exc:
        raise ConfigEntryAuthFailed("Log in failed for %s: %s", DOMAIN, exc)
    except Exception as exc:
        _LOGGER.exception("Login with %s failed: %s", DOMAIN, exc)
        return False

    if entry.version == 1:
        # v1 did not enforce a unique id for the config_entry. Fixing this in v2.1

        new_version = 2
        new_minor_version = 1
        _LOGGER.info("Starting migration to config schema v2.1.")

        if not entry.unique_id or entry.unique_id == "":
            _LOGGER.debug("Unique_id is missing. Adding it.")

            user = await myskoda.get_user()
            unique_id = user.id

            _LOGGER.debug("Adding unique_id %s to entry %s", unique_id, entry.entry_id)
            hass.config_entries.async_update_entry(
                entry,
                version=new_version,
                minor_version=new_minor_version,
                unique_id=unique_id,
            )
            return True

        else:
            _LOGGER.debug(
                "Detected unique_id. Skipping generation, only updating schema version"
            )
            hass.config_entries.async_update_entry(
                entry, version=new_version, minor_version=new_minor_version
            )

            return True

    if entry.version == 2:
        if entry.minor_version < 2:
            # v2.1 does not have the vinlist. Add it.
            _LOGGER.info("Starting migration to config schema 2.2, adding vinlist")

            new_version = 2
            new_minor_version = 2

            entry_data = {**entry.data}

            vinlist = await myskoda.list_vehicle_vins()
            entry_data[VINLIST] = vinlist
            _LOGGER.debug("Add vinlist %s to entry %s", vinlist, entry.entry_id)

            hass.config_entries.async_update_entry(
                entry,
                version=new_version,
                minor_version=new_minor_version,
                data=entry_data,
            )

            return True

    # Add any more migrations here

    return False
