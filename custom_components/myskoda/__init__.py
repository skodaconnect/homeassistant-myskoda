"""The MySkoda integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from aiohttp import ClientResponseError, InvalidUrlClientError
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    ServiceValidationError,
)
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.util.ssl import get_default_context

from myskoda import (
    AuthorizationFailedError,
    MySkoda,
)
from myskoda.models.departure import DepartureTimer
from myskoda.models.info import CapabilityId
from myskoda.mqtt import OperationFailedError
from myskoda.models.common import Vin
from myskoda.myskoda import TRACE_CONFIG
from myskoda.auth.authorization import (
    CSRFError,
    MarketingConsentError,
    TermsAndConditionsError,
    TokenExpiredError,
)

from .const import (
    CONF_FCM_TOKEN,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_USERNAME,
    CONF_VINLIST,
    DOMAIN,
    SERVICE_SET_DEPARTURE_TIMER,
)
from .coordinator import MySkodaConfigEntry, MySkodaDataUpdateCoordinator
from .error_handlers import handle_aiohttp_error
from .issues import (
    async_create_tnc_issue,
    async_delete_spin_issue,
    async_delete_tnc_issue,
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

SERVICE_SET_DEPARTURE_TIMER_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("timer"): vol.Schema(
            {
                vol.Required("id"): vol.In([1, 2, 3]),
                vol.Required("enabled"): bool,
            },
            extra=vol.ALLOW_EXTRA,
        ),
    }
)


async def _async_handle_set_departure_timer(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Handle the set_departure_timer service call."""
    device_id: str = call.data["device_id"]
    timer_data: dict = call.data["timer"]

    # Resolve device VIN
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get(device_id)
    if device is None:
        raise ServiceValidationError(f"Device '{device_id}' not found")

    vin: str | None = next(
        (ident[1] for ident in device.identifiers if ident[0] == DOMAIN),
        None,
    )
    if vin is None:
        raise ServiceValidationError(
            f"Device '{device_id}' VIN not found. Set up the {DOMAIN} integration again"
        )

    # Find coordinator for this VIN
    coordinator: MySkodaDataUpdateCoordinator | None = None
    for entry_data in hass.data.get(DOMAIN, {}).values():
        coordinators = entry_data.get(COORDINATORS, {})
        if vin in coordinators:
            coordinator = coordinators[vin]
            break

    if coordinator is None:
        raise ServiceValidationError(f"No coordinator found for VIN '{vin}'")

    # Check capability
    if not coordinator.data.vehicle.has_capability(CapabilityId.DEPARTURE_TIMERS):
        raise ServiceValidationError(
            f"Vehicle '{vin}' does not support departure timers"
        )

    # Parse timer from dict
    try:
        timer = DepartureTimer.from_dict(timer_data)
    except (TypeError, ValueError, KeyError) as exc:
        raise ServiceValidationError(f"Invalid timer configuration: {exc}") from exc

    # All seems good. Send to vehicle
    try:
        await coordinator.myskoda.set_departure_timer(vin, timer)
    except (ClientResponseError, OperationFailedError) as exc:
        raise ServiceValidationError(f"Failed to set departure timer: {exc}") from exc

    await coordinator.async_request_refresh()


def myskoda_instantiate(
    hass: HomeAssistant, entry: MySkodaConfigEntry, mqtt_enabled: bool = True
) -> MySkoda:
    """Generic connector to MySkoda REST API."""

    trace_configs = []
    if entry.options.get("tracing"):
        trace_configs.append(TRACE_CONFIG)

    session = async_create_clientsession(
        hass, trace_configs=trace_configs, auto_cleanup=False
    )
    return MySkoda(session, get_default_context(), mqtt_enabled=mqtt_enabled)


async def auto_connect(myskoda: MySkoda, entry: MySkodaConfigEntry) -> None:
    """Figure out if we can use the refresh token or if we should fall back to username/password. Then attempt to authenticate."""

    connect_kwargs = {
        "email": entry.data[CONF_USERNAME],
        "password": entry.data[CONF_PASSWORD],
        "refresh_token": entry.data.get(CONF_REFRESH_TOKEN),
        "fcm_token": entry.data.get(CONF_FCM_TOKEN),
    }
    _LOGGER.debug(
        "Authorizing with %s",
        "refresh token'" if connect_kwargs["refresh_token"] else "username/password",
    )
    try:
        await myskoda.connect(**connect_kwargs)
    except TokenExpiredError:
        _LOGGER.debug("Refresh token is expired. Falling back to username/password")
        connect_kwargs.pop("refresh_token")
        await myskoda.connect(**connect_kwargs)


async def async_setup_entry(hass: HomeAssistant, entry: MySkodaConfigEntry) -> bool:
    """Set up MySkoda integration from a config entry."""

    myskoda = myskoda_instantiate(hass, entry, mqtt_enabled=False)

    try:
        await auto_connect(myskoda, entry)
    except AuthorizationFailedError as exc:
        _LOGGER.debug("Authorization with MySkoda failed.")
        raise ConfigEntryAuthFailed from exc
    except (TermsAndConditionsError, MarketingConsentError) as exc:
        _LOGGER.error(
            "Terms or marketing consent missing. Log out and back in with official MySkoda app, "
            "or https://skodaid.vwgroup.io, to accept the new conditions. Error: %s",
            exc,
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

    # At this point we are fully connected and authorized

    async_delete_tnc_issue(hass, entry.entry_id)
    async_delete_spin_issue(hass, entry.entry_id)

    coordinators: dict[Vin, MySkodaDataUpdateCoordinator] = {}
    cached_vins: list = entry.data.get(CONF_VINLIST, [])

    try:
        vehicles = await myskoda.list_vehicle_vins()
        if vehicles and vehicles != cached_vins:
            _LOGGER.info("New vehicles detected. Storing new vehicle list in cache")
            entry_data = {**entry.data}
            entry_data[CONF_VINLIST] = vehicles
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

    if entry.data.get(CONF_REFRESH_TOKEN):
        current_refresh_token = await myskoda.get_refresh_token()
        if current_refresh_token != entry.data[CONF_REFRESH_TOKEN]:
            _LOGGER.debug(
                "Refresh token updated during initialization. Storing new token in configuration."
            )
            new_data = {**entry.data}
            new_data[CONF_REFRESH_TOKEN] = current_refresh_token
            hass.config_entries.async_update_entry(entry, data=new_data)

    for vin in vehicles:
        coordinator = MySkodaDataUpdateCoordinator(hass, entry, myskoda, vin)
        await coordinator.async_config_entry_first_refresh()
        coordinators[vin] = coordinator

    entry.runtime_data = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_SET_DEPARTURE_TIMER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_DEPARTURE_TIMER,
            lambda call: _async_handle_set_departure_timer(hass, call),
            schema=SERVICE_SET_DEPARTURE_TIMER_SCHEMA,
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: MySkodaConfigEntry) -> bool:
    """Unload a config entry."""

    coordinators: dict[Vin, MySkodaDataUpdateCoordinator] = entry.runtime_data
    for coord in coordinators.values():
        if entry.data.get(CONF_REFRESH_TOKEN):
            current_refresh_token = await coord.myskoda.get_refresh_token()
            if current_refresh_token != entry.data[CONF_REFRESH_TOKEN]:
                _LOGGER.info("Saving authorization refresh token before shutdown")
                entry_data = {**entry.data}
                entry_data[CONF_REFRESH_TOKEN] = current_refresh_token
                hass.config_entries.async_update_entry(entry, data=entry_data)
        if coord.myskoda.fcm_token and coord.myskoda.fcm_token != entry.data.get(
            CONF_FCM_TOKEN
        ):
            _LOGGER.info("Saving FCM token before shutdown")
            entry_data = {**entry.data}
            entry_data[CONF_FCM_TOKEN] = coord.myskoda.fcm_token
            hass.config_entries.async_update_entry(entry, data=entry_data)
        await coord.myskoda.disconnect()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: MySkodaConfigEntry):
    """Handle options update."""
    # Do a lazy reload of integration when configuration changed
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: MySkodaConfigEntry) -> bool:
    """Handle MySkoda config-entry schema migrations."""

    _LOGGER.debug(
        "Starting migration of config entry %s from v%s.%s",
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
            "Configuration for %s is too new. This can happen if you downgraded your HA install or integration. Automatic configuration migration aborted.",
            DOMAIN,
        )
        return False

    entry_data = {**entry.data}

    # We will likely need to contact myskoda, so make a connection and authenticate
    try:
        myskoda = myskoda_instantiate(hass, entry, mqtt_enabled=False)
        await auto_connect(myskoda, entry)
    except AuthorizationFailedError as exc:
        raise ConfigEntryAuthFailed("Log in failed for %s: %s", DOMAIN, exc)
    except (TermsAndConditionsError, MarketingConsentError) as exc:
        _LOGGER.error(
            "Terms or marketing consent missing. Log out and back in with official MySkoda app, "
            "or https://skodaid.vwgroup.io, to accept the new conditions. Error: %s",
            exc,
        )
        async_create_tnc_issue(hass, entry.entry_id)
        raise ConfigEntryNotReady from exc
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

        else:
            _LOGGER.debug(
                "Detected unique_id. Skipping generation, only updating schema version"
            )
            hass.config_entries.async_update_entry(
                entry, version=new_version, minor_version=new_minor_version
            )

    if entry.version == 2:
        if entry.minor_version < 2:
            # v2.1 does not have the vinlist. Add it.
            _LOGGER.info("Starting migration to config schema 2.2, adding vinlist")

            new_version = 2
            new_minor_version = 2

            vinlist = await myskoda.list_vehicle_vins()
            entry_data[CONF_VINLIST] = vinlist
            _LOGGER.debug("Add vinlist %s to entry %s", vinlist, entry.entry_id)

            hass.config_entries.async_update_entry(
                entry,
                version=new_version,
                minor_version=new_minor_version,
                data=entry_data,
            )

        vinlist = entry_data[CONF_VINLIST]
        if entry.minor_version < 3:
            # Remove unneeded generate_fixtures button
            _LOGGER.info(
                "Starting migration to config schema 2.3, removing deprecated fixtures button"
            )

            new_version = 2
            new_minor_version = 3

            hass_er = er.async_get(hass)
            entry_entities = er.async_entries_for_config_entry(hass_er, entry.entry_id)
            vin_set = {f"{vin}_generate_fixtures" for vin in vinlist}

            for entity in entry_entities:
                if entity.unique_id in vin_set:
                    _LOGGER.debug(
                        "Removing entity %s, it is no longer supported",
                        entity.unique_id,
                    )
                    hass_er.async_remove(entity.entity_id)

            hass.config_entries.async_update_entry(
                entry,
                version=new_version,
                minor_version=new_minor_version,
                data=entry_data,
            )

        if entry.minor_version < 4:
            # Rename "locked" binary sensor to "lock" to prevent confusion
            _LOGGER.info(
                "Starting migration to config schema 2.4, renaming _locked to _lock"
            )

            new_version = 2
            new_minor_version = 4

            hass_er = er.async_get(hass)
            entry_entities = er.async_entries_for_config_entry(hass_er, entry.entry_id)

            old_entities = []
            old_entities.extend(f"{vin}_charger_locked" for vin in vinlist)
            old_entities.extend(f"{vin}_doors_locked" for vin in vinlist)
            old_entities.extend(f"{vin}_locked" for vin in vinlist)

            for entity in entry_entities:
                if entity.unique_id in old_entities:
                    if entity.unique_id.endswith(("charger_locked", "doors_locked")):
                        new_unique_id = entity.unique_id.replace("locked", "lock")
                    else:
                        new_unique_id = entity.unique_id.replace(
                            "locked", "vehicle_lock"
                        )
                    _LOGGER.debug(
                        "Renaming entity %s to %s", entity.unique_id, new_unique_id
                    )
                    try:
                        hass_er.async_update_entity(
                            entity.entity_id, new_unique_id=new_unique_id
                        )
                    except ValueError:
                        _LOGGER.error(
                            "Failure migrating %s: Entity already exists when updating entity %s to new unique_id %s",
                            entry.entry_id,
                            entity.entity_id,
                            new_unique_id,
                        )
                        return False

            hass.config_entries.async_update_entry(
                entry,
                version=new_version,
                minor_version=new_minor_version,
                data=entry_data,
            )

        if entry.minor_version < 5:
            # Add support for refresh_token
            _LOGGER.info(
                "Starting migration to config schema 2.5, adding support for refresh_token"
            )

            new_version = 2
            new_minor_version = 5

            if entry.data.get(CONF_REFRESH_TOKEN):
                _LOGGER.warning(
                    "Found refresh token present, this should not happen. Possible data corruption. Please open an issue for this with the integration developers"
                )
                return False
            else:
                current_refresh_token = await myskoda.get_refresh_token()
                entry_data[CONF_REFRESH_TOKEN] = current_refresh_token
                _LOGGER.debug(
                    "Saving current refresh token as initial token: %s",
                    current_refresh_token,
                )
                hass.config_entries.async_update_entry(
                    entry,
                    version=new_version,
                    minor_version=new_minor_version,
                    data=entry_data,
                )

        # Add any more minor migrations here. Minor migrations only add or change data. Removals are major.

    # Add any more major migrations here

    _LOGGER.info(
        "Config migration finished. Now at schema version v%s.%s",
        entry.version,
        entry.minor_version,
    )

    return True
