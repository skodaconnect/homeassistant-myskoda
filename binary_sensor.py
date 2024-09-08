"""Oilfox metering."""

from pickle import TRUE

from .entity import EnyaqDataEntity, EnyaqEntity

from .enyaq import EnyaqHub, Vehicle
from .const import DATA_COODINATOR, DOMAIN
from homeassistant.components.binary_sensor import (
    BinarySensorEntityDescription,
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)


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
        entities.append(EnyaqBinarySensorChargerConnected(coordinator, vehicle))
        entities.append(EnyaqBinarySensorChargerLocked(coordinator, vehicle))
        entities.append(EnyaqBinarySensorLocked(coordinator, vehicle))
        entities.append(EnyaqBinarySensorDoorsLocked(coordinator, vehicle))
        entities.append(EnyaqBinarySensorDoorsOpen(coordinator, vehicle))
        entities.append(EnyaqBinarySensorWindowsOpen(coordinator, vehicle))
        entities.append(EnyaqBinarySensorTrunkOpen(coordinator, vehicle))
        entities.append(EnyaqBinarySensorBonnetOpen(coordinator, vehicle))
        entities.append(EnyaqBinarySensorLightsOn(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class EnyaqBinarySensor(EnyaqDataEntity, BinarySensorEntity):
    """Base class for all Enyaq binary sensors."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        vehicle: Vehicle,
        entity_description: EntityDescription,
    ) -> None:
        super().__init__(coordinator, vehicle, entity_description)
        BinarySensorEntity.__init__(self)


class EnyaqBinarySensorChargerConnected(EnyaqBinarySensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="charger_connected",
                name=f"{vehicle.info.title} Charger Connected",
                device_class=BinarySensorDeviceClass.PLUG,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_charger_connected"

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.air_conditioning.charger_connected

    @property
    def icon(self):
        if not self.coordinator.data:
            return "mdi:power_plug"

        self._update_device_from_coordinator()

        if self.vehicle.charging.state == "CONNECT_CABLE":
            return "mdi:power-plug-off"
        else:
            return "mdi:power-plug"


class EnyaqBinarySensorChargerLocked(EnyaqBinarySensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="charger_locked",
                name=f"{vehicle.info.title} Charger",
                device_class=BinarySensorDeviceClass.LOCK,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_charger_locked"

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return not self.vehicle.air_conditioning.charger_locked

    @property
    def icon(self):
        if not self.coordinator.data:
            return "mdi:lock"

        self._update_device_from_coordinator()

        if self.vehicle.air_conditioning.charger_locked:
            return "mdi:lock"
        else:
            return "mdi:lock-open"


class EnyaqBinarySensorLocked(EnyaqBinarySensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="locked",
                name=f"{vehicle.info.title} Locks",
                device_class=BinarySensorDeviceClass.LOCK,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_locked"

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return not self.vehicle.status.locked

    @property
    def icon(self):
        if not self.coordinator.data:
            return "mdi:lock"

        self._update_device_from_coordinator()

        if self.is_on:
            return "mdi:lock-open"
        else:
            return "mdi:lock"


class EnyaqBinarySensorDoorsLocked(EnyaqBinarySensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="doors_locked",
                name=f"{vehicle.info.title} Doors Locks",
                device_class=BinarySensorDeviceClass.LOCK,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_doors_locked"

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return not self.vehicle.status.doors_locked

    @property
    def icon(self):
        if not self.coordinator.data:
            return "mdi:lock"

        self._update_device_from_coordinator()

        if self.is_on:
            return "mdi:car-door-lock-open"
        else:
            return "mdi:car-door-lock"


class EnyaqBinarySensorDoorsOpen(EnyaqBinarySensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="doors_open",
                name=f"{vehicle.info.title} Doors",
                device_class=BinarySensorDeviceClass.DOOR,
                icon="mdi:car-door",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_doors_open"

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.status.doors_open


class EnyaqBinarySensorWindowsOpen(EnyaqBinarySensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="windows_open",
                name=f"{vehicle.info.title} Windows",
                device_class=BinarySensorDeviceClass.WINDOW,
                icon="mdi:car-door",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_windows_open"

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.status.windows_open


class EnyaqBinarySensorTrunkOpen(EnyaqBinarySensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="trunk_open",
                name=f"{vehicle.info.title} Trunk",
                device_class=BinarySensorDeviceClass.OPENING,
                icon="mdi:car",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_trunk_open"

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.status.trunk_open


class EnyaqBinarySensorBonnetOpen(EnyaqBinarySensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="bonnet_open",
                name=f"{vehicle.info.title} Bonnet",
                device_class=BinarySensorDeviceClass.OPENING,
                icon="mdi:car",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_bonnet_open"

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.status.bonnet_open


class EnyaqBinarySensorLightsOn(EnyaqBinarySensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="lights_on",
                name=f"{vehicle.info.title} Lights",
                device_class=BinarySensorDeviceClass.LIGHT,
                icon="mdi:car-light-high",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_lights_on"

    @property
    def is_on(self):
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.status.lights_on
