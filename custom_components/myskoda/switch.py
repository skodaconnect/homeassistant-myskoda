"""Switches for the MySkoda integration."""

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
from myskoda import Vehicle

from .const import DATA_COODINATOR, DOMAIN
from .entity import MySkodaDataEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config.entry_id][DATA_COODINATOR]

    vehicles = coordinator.data.get("vehicles")

    entities = []

    for vehicle in vehicles:
        entities.append(WindowHeating(coordinator, vehicle))
        entities.append(ReducedCurrent(coordinator, vehicle))
        entities.append(BatteryCareMode(coordinator, vehicle))
        entities.append(Charging(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class MySkodaSwitch(MySkodaDataEntity, SwitchEntity):
    """Base class for all switches in the MySkoda integration."""

    def __init__(  # noqa: D107
        self,
        coordinator: DataUpdateCoordinator,
        vehicle: Vehicle,
        entity_description: SwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator, vehicle, entity_description)
        SwitchEntity.__init__(self)


class WindowHeating(MySkodaSwitch):
    """Controls window heating."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
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
    def is_on(self) -> bool | None:  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return (
            self.vehicle.air_conditioning.window_heating_front_on
            or self.vehicle.air_conditioning.window_heating_rear_on
        )

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self.coordinator.hub.stop_window_heating(self.vehicle.info.vin)
        for _ in range(10):
            await sleep(15)
            if not self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.debug("Window heating disabled.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self.coordinator.hub.start_window_heating(self.vehicle.info.vin)
        for _ in range(10):
            await sleep(15)
            if self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.debug("Window heating enabled.")


class BatteryCareMode(MySkodaSwitch):
    """Controls battery care mode."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
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
    def is_on(self) -> bool | None:  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.charging_care_mode

    async def async_turn_off(self, **kwargs):  # noqa: D102 # noqa: D102
        await self.coordinator.hub.set_battery_care_mode(self.vehicle.info.vin, False)
        for _ in range(10):
            await sleep(15)
            if not self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Battery care mode disabled.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self.coordinator.hub.set_battery_care_mode(self.vehicle.info.vin, True)
        for _ in range(10):
            await sleep(15)
            if self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Battery care mode enabled.")


class ReducedCurrent(MySkodaSwitch):
    """Control whether to charge with reduced current."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
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
    def is_on(self) -> bool | None:  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.use_reduced_current

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self.coordinator.hub.set_reduced_current_limit(
            self.vehicle.info.vin, False
        )
        for _ in range(10):
            await sleep(15)
            if not self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Reduced current limit disabled.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self.coordinator.hub.set_reduced_current_limit(
            self.vehicle.info.vin, True
        )
        for _ in range(10):
            await sleep(15)
            if self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Reduced current limit enabled.")


class Charging(MySkodaSwitch):
    """Control whether the vehicle should be charging."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            SwitchEntityDescription(
                key="charging",
                name=f"{vehicle.info.title} Charging",
                icon="mdi:power-plug-battery",
                device_class=SwitchDeviceClass.SWITCH,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_charging"

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.state == "CHARGING"

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self.coordinator.hub.stop_charging(self.vehicle.info.vin)
        for _ in range(10):
            await sleep(15)
            if not self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Charging stopped.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self.coordinator.hub.start_charging(self.vehicle.info.vin)
        for _ in range(10):
            await sleep(15)
            if self.is_on:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("Charging started.")
