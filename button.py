"""Enyaq Switches."""

import logging

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .entity import EnyaqDataEntity
from .enyaq import Vehicle
from .const import DATA_COODINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config.entry_id][DATA_COODINATOR]

    vehicles = coordinator.data

    entities = []

    for vehicle in vehicles:
        entities.append(EnyaqButtonStartCharging(coordinator, vehicle))
        entities.append(EnyaqButtonStopCharging(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class EnyaqButton(EnyaqDataEntity, ButtonEntity):
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        vehicle: Vehicle,
        entity_description: ButtonEntityDescription,
    ) -> None:
        super().__init__(coordinator, vehicle, entity_description)
        ButtonEntity.__init__(self)


class EnyaqButtonStopCharging(EnyaqButton):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            ButtonEntityDescription(
                key="stop_charging",
                name=f"{vehicle.info.title} Stop Charging",
                icon="mdi:power-plug-battery-outline",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_stop_charging"

    async def async_press(self):
        await self.coordinator.hub.stop_charging(self.vehicle.info.vin)
        _LOGGER.info("Charging stopped.")


class EnyaqButtonStartCharging(EnyaqButton):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            ButtonEntityDescription(
                key="start_charging",
                name=f"{vehicle.info.title} Start Charging",
                icon="mdi:power-plug-battery",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_start_charging"

    async def async_press(self):
        await self.coordinator.hub.start_charging(self.vehicle.info.vin)
        _LOGGER.info("Charging started.")
