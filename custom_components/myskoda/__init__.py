"""The MySkoda integration."""

from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.ssl import get_default_context
from myskoda import MySkoda

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
]


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Set up MySkoda integration from a config entry."""

    myskoda = MySkoda(async_get_clientsession(hass))

    try:
        await myskoda.connect(
            config.data["email"], config.data["password"], get_default_context()
        )
    except Exception:
        _LOGGER.error("Login with MySkoda failed.")
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

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
