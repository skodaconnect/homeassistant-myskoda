"""The MySkoda Enyaq integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from myskoda import RestApi, Vehicle

from .const import DATA_COODINATOR, DOMAIN

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
    """Set up Enyaq integration from a config entry."""

    coordinator = MySkodaDataUpdateCoordinator(hass, config)

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


class MySkodaDataUpdateCoordinator(DataUpdateCoordinator):
    """See `DataUpdateCoordinator`.

    This class manages all data from the MySkoda API.
    """

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Create a new coordinator."""

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=5)
        )
        self.hub = RestApi(async_get_clientsession(hass))
        self.config = config

    async def async_login(self) -> bool:
        """Login to the MySkoda API. Will return `True` if successful."""

        return await self.hub.authenticate(
            self.config.data["email"], self.config.data["password"]
        )

    async def _async_update_data(self) -> dict[str, list[Vehicle]]:
        return {
            "vehicles": await self.hub.get_all_vehicles(),
        }

    def _unsub_refresh(self):
        return
