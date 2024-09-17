"""Binary Sensors for MySkoda."""

from typing import cast
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from myskoda import Vehicle, charging, common
from myskoda.models.common import DoorLockedState, OnOffState, OpenState

from .const import DATA_COODINATOR, DOMAIN
from .entity import MySkodaDataEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config.entry_id][DATA_COODINATOR]

    vehicles = cast(list[Vehicle], coordinator.data.get("vehicles"))

    entities = []

    for vehicle in vehicles:
        entities.append(Locked(coordinator, vehicle))
        entities.append(DoorsLocked(coordinator, vehicle))
        entities.append(DoorsOpen(coordinator, vehicle))
        entities.append(WindowsOpen(coordinator, vehicle))
        entities.append(TrunkOpen(coordinator, vehicle))
        entities.append(BonnetOpen(coordinator, vehicle))
        entities.append(LightsOn(coordinator, vehicle))
        if vehicle.charging and vehicle.charging.status:
            entities.append(ChargerConnected(coordinator, vehicle))
            entities.append(ChargerLocked(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class MySkodaBinarySensor(MySkodaDataEntity, BinarySensorEntity):
    """Base class for all MySkoda binary sensors."""

    def __init__(  # noqa: D107
        self,
        coordinator: DataUpdateCoordinator,
        vehicle: Vehicle,
        entity_description: EntityDescription,
    ) -> None:
        super().__init__(coordinator, vehicle, entity_description)
        BinarySensorEntity.__init__(self)


class ChargerConnected(MySkodaBinarySensor):
    """Detects if the charger is connected to the car."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="charger_connected",
                name=f"{vehicle.info.specification.title} Charger Connected",
                device_class=BinarySensorDeviceClass.PLUG,
                translation_key="charger_connected",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_charger_connected"

    @property
    def is_on(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return (
            self.vehicle.air_conditioning.charger_connection_state
            == common.ConnectionState.CONNECTED
        )

    @property
    def icon(self):  # noqa: D102
        if not self.coordinator.data or not self.vehicle.charging.status:
            return "mdi:power_plug"

        self._update_device_from_coordinator()

        if self.vehicle.charging.status.state == charging.ChargingState.CONNECT_CABLE:
            return "mdi:power-plug-off"
        return "mdi:power-plug"


class ChargerLocked(MySkodaBinarySensor):
    """Detect if the charger is locked on the car, or whether it can be unplugged."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="charger_locked",
                name=f"{vehicle.info.specification.title} Charger",
                device_class=BinarySensorDeviceClass.LOCK,
                translation_key="charger_locked",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_charger_locked"

    @property
    def is_on(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return (
            self.vehicle.air_conditioning.charger_lock_state
            != common.ChargerLockedState.LOCKED
        )

    @property
    def icon(self):  # noqa: D102
        if not self.coordinator.data:
            return "mdi:lock"

        self._update_device_from_coordinator()

        if (
            self.vehicle.air_conditioning.charger_lock_state
            == common.ChargerLockedState.LOCKED
        ):
            return "mdi:lock"
        return "mdi:lock-open"


class Locked(MySkodaBinarySensor):
    """Detects whether the vehicle is fully locked."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="locked",
                name=f"{vehicle.info.specification.title} Locks",
                device_class=BinarySensorDeviceClass.LOCK,
                translation_key="locked",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_locked"

    @property
    def is_on(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return not self.vehicle.status.overall.locked == DoorLockedState.UNLOCKED

    @property
    def icon(self):  # noqa: D102
        if not self.coordinator.data:
            return "mdi:lock"

        self._update_device_from_coordinator()

        if self.is_on:
            return "mdi:lock-open"
        return "mdi:lock"


class DoorsLocked(MySkodaBinarySensor):
    """Detect whether the doors are locked."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="doors_locked",
                name=f"{vehicle.info.specification.title} Doors Locks",
                device_class=BinarySensorDeviceClass.LOCK,
                translation_key="doors_locked",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_doors_locked"

    @property
    def is_on(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return not self.vehicle.status.overall.doors_locked == DoorLockedState.UNLOCKED

    @property
    def icon(self):  # noqa: D102
        if not self.coordinator.data:
            return "mdi:lock"

        self._update_device_from_coordinator()

        if self.is_on:
            return "mdi:car-door-lock-open"
        return "mdi:car-door-lock"


class DoorsOpen(MySkodaBinarySensor):
    """Detects whether at least one door is open."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="doors_open",
                name=f"{vehicle.info.specification.title} Doors",
                device_class=BinarySensorDeviceClass.DOOR,
                icon="mdi:car-door",
                translation_key="doors_open",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_doors_open"

    @property
    def is_on(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.status.overall.doors == OpenState.OPEN


class WindowsOpen(MySkodaBinarySensor):
    """Detects whether at least one window is open."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="windows_open",
                name=f"{vehicle.info.specification.title} Windows",
                device_class=BinarySensorDeviceClass.WINDOW,
                icon="mdi:car-door",
                translation_key="windows_open",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_windows_open"

    @property
    def is_on(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.status.overall.windows == OpenState.OPEN


class TrunkOpen(MySkodaBinarySensor):
    """Detects whether the trunk is open."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="trunk_open",
                name=f"{vehicle.info.specification.title} Trunk",
                device_class=BinarySensorDeviceClass.OPENING,
                icon="mdi:car",
                translation_key="trunk_open",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_trunk_open"

    @property
    def is_on(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.status.detail.trunk == OpenState.OPEN


class BonnetOpen(MySkodaBinarySensor):
    """Detects whether the bonnet is open."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="bonnet_open",
                name=f"{vehicle.info.specification.title} Bonnet",
                device_class=BinarySensorDeviceClass.OPENING,
                icon="mdi:car",
                translation_key="bonnet_open",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_bonnet_open"

    @property
    def is_on(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.status.detail.bonnet == OpenState.OPEN


class LightsOn(MySkodaBinarySensor):
    """Detects whether the lights are on."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            BinarySensorEntityDescription(
                key="lights_on",
                name=f"{vehicle.info.specification.title} Lights",
                device_class=BinarySensorDeviceClass.LIGHT,
                icon="mdi:car-light-high",
                translation_key="lights_on",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_lights_on"

    @property
    def is_on(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.status.overall.lights == OnOffState.ON
