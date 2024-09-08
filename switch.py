"""Enyaq Switches."""

from asyncio import sleep
import logging

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
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
        entities.append(EnyaqWindowHeatingSwitch(coordinator, vehicle))
        entities.append(EnyaqReducedCurrentSwitch(coordinator, vehicle))
        entities.append(EnyaqBatteryCareModeSwitch(coordinator, vehicle))

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
            if not self.is_on:
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

class EnyaqBatteryCareModeSwitch(EnyaqSwitch):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            SwitchEntityDescription(
                key="battery_care_mode",
                name=f"{vehicle.info.title} Battery Care Mode",
                icon="mdi:battery-heart-variant",
                device_class=SwitchDeviceClass.SWITCH,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_battery_care_mode"

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.charging_care_mode

    async def async_turn_off(self, **kwargs):
        await self.coordinator.hub.set_battery_care_mode(self.vehicle.info.vin, False)
        for i in range(0, 10):
            await sleep(15)
            if not self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Battery care mode disabled.")

    async def async_turn_on(self, **kwargs):
        await self.coordinator.hub.set_battery_care_mode(self.vehicle.info.vin, True)
        for i in range(0, 10):
            await sleep(15)
            if self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Battery care mode enabled.")

class EnyaqReducedCurrentSwitch(EnyaqSwitch):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            SwitchEntityDescription(
                key="reduced_current",
                name=f"{vehicle.info.title} Reduced Current",
                icon="mdi:current-ac",
                device_class=SwitchDeviceClass.SWITCH,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_reduced_current"

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.use_reduced_current

    async def async_turn_off(self, **kwargs):
        await self.coordinator.hub.set_reduced_current_limit(self.vehicle.info.vin, False)
        for i in range(0, 10):
            await sleep(15)
            if not self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Reduced current limit disabled.")

    async def async_turn_on(self, **kwargs):
        await self.coordinator.hub.set_reduced_current_limit(self.vehicle.info.vin, True)
        for i in range(0, 10):
            await sleep(15)
            if self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Reduced current limit enabled.")
