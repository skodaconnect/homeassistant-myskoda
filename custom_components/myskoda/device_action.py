"""Actions (services) for the MySkoda integration."""

import logging

import voluptuous as vol
from aiohttp import ClientResponseError
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from myskoda.models.chargingprofiles import ChargingProfile, ChargingTimes
from myskoda.mqtt import OperationFailedError

from .const import CONF_READONLY, DOMAIN, SERVICE_SET_CHARGING_PROFILE_TIME
from .coordinator import MySkodaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_CHARGING_PROFILE_TIME_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("id"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required("enabled"): cv.boolean,
        vol.Required("start_time"): cv.time,
        vol.Required("end_time"): cv.time,
    }
)


def _resolve_charging_profile(
    hass: HomeAssistant, device_id: str
) -> tuple[MySkodaDataUpdateCoordinator, ChargingProfile] | None:
    """Resolve a charging-profile device_id to its coordinator and ChargingProfile.

    Only accepts devices created for a charging profile (children of a vehicle
    device via `via_device`), not the vehicle device itself.
    """
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    if not device or not device.via_device_id:
        return None

    vehicle_device = device_registry.async_get(device.via_device_id)
    if not vehicle_device:
        return None

    vin = next(
        (
            identifier
            for domain, identifier in vehicle_device.identifiers
            if domain == DOMAIN
        ),
        None,
    )
    if not vin:
        return None

    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinators = getattr(entry, "runtime_data", None)
        coordinator = coordinators.get(vin) if coordinators else None
        if not coordinator or not coordinator.data:
            continue

        profiles = coordinator.data.charging_profiles
        if not profiles:
            continue

        for profile in profiles.charging_profiles:
            expected_identifier = (DOMAIN, f"{vin}_charging_profile_{profile.id}")
            if expected_identifier in device.identifiers:
                return coordinator, profile

    return None


async def _async_handle_set_charging_profile_time(call: ServiceCall) -> None:
    """Handle the set_charging_profile_time action."""
    resolved = _resolve_charging_profile(call.hass, call.data["device_id"])
    if not resolved:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="charging_profile_not_found",
        )
    coordinator, profile = resolved

    if coordinator.entry.options.get(CONF_READONLY):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="readonly_mode",
        )

    times_id = call.data["id"]
    if not any(times.id == times_id for times in profile.preferred_charging_times):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="charging_time_not_found",
        )

    times = ChargingTimes(
        id=times_id,
        enabled=call.data["enabled"],
        start_time=call.data["start_time"],
        end_time=call.data["end_time"],
    )

    try:
        await coordinator.myskoda.set_preferred_charging_times(
            coordinator.vin, profile.id, times
        )
    except (ClientResponseError, OperationFailedError) as exc:
        _LOGGER.error("Failed to set charging profile time: %s", exc)
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="charging_time_update_failed",
        ) from exc


def async_setup_actions(hass: HomeAssistant) -> None:
    """Register the MySkoda actions.

    Called once from `async_setup`, which HA invokes exactly once per run
    regardless of how many config entries exist, so the service is never
    registered twice and needs no per-entry unload bookkeeping.
    """
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CHARGING_PROFILE_TIME,
        _async_handle_set_charging_profile_time,
        schema=SERVICE_SET_CHARGING_PROFILE_TIME_SCHEMA,
    )
