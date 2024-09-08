"""The Oilfox integration."""

from __future__ import annotations
from datetime import timedelta
import logging
from pickle import FALSE

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .enyaq import EnyaqHub, Vehicle

from .const import DATA_COODINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.CLIMATE,
    Platform.SWITCH,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Set up Enyaq integration from a config entry."""

    coordinator = EnyaqDataUpdateCoordinator(hass, config)

    if not await coordinator.async_login():
        return False

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config.entry_id] = {DATA_COODINATOR: coordinator}

    await hass.config_entries.async_forward_entry_setups(config, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class EnyaqDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=5)
        )
        self.hub = EnyaqHub(async_get_clientsession(hass))
        self.config = config

    async def async_login(self) -> bool:
        login_success = await self.hub.authenticate(
            self.config.data["email"], self.config.data["password"]
        )
        return login_success

    async def _async_update_data(self) -> list[Vehicle]:
        return await self.hub.get_all_vehicles()

    def _unsub_refresh(self):
        return
