"""Oilfox metering."""

from asyncio import sleep
from pickle import TRUE
import logging

from .entity import EnyaqDataEntity, EnyaqEntity

from .enyaq import EnyaqHub, Vehicle
from .const import DATA_COODINATOR, DOMAIN
from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

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
        entities.append(EnyaqWindowHeatingSwitch(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class EnyaqSwitch(EnyaqDataEntity, SwitchEntity):
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        vehicle: Vehicle,
        entity_description: SwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator, vehicle, entity_description)
        SwitchEntity.__init__(self)


class EnyaqWindowHeatingSwitch(EnyaqSwitch):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            SwitchEntityDescription(
                key="window_heating",
                name=f"{vehicle.info.title} Window Heating",
                icon="mdi:car-defrost-front",
                device_class=SwitchDeviceClass.SWITCH,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_window_heating"

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return (
            self.vehicle.air_conditioning.window_heating_front_on
            or self.vehicle.air_conditioning.window_heating_rear_on
        )

    async def async_turn_off(self, **kwargs):
        await self.coordinator.hub.stop_window_heating(self.vehicle.info.vin)
        for i in range(0, 10):
            await sleep(15)
            if self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Window heating disabled.")

    async def async_turn_on(self, **kwargs):
        await self.coordinator.hub.start_window_heating(self.vehicle.info.vin)
        for i in range(0, 10):
            await sleep(15)
            if self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Window heating enabled.")
