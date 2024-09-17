"""Binary Sensors for MySkoda."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from myskoda import common
from myskoda.models.air_conditioning import AirConditioning
from myskoda.models.common import DoorLockedState, OnOffState, OpenState
from myskoda.models.info import CapabilityId
from myskoda.models.status import Status

from .entity import MySkodaEntity
from .utils import (
    InvalidCapabilityConfigurationError,
    add_supported_entities,
)

from .const import COORDINATOR, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    add_supported_entities(
        available_entities=[
            Locked,
            DoorsLocked,
            DoorsOpen,
            WindowsOpen,
            TrunkOpen,
            BonnetOpen,
            LightsOn,
            ChargerConnected,
            ChargerLocked,
            SunroofOpen,
        ],
        coordinator=hass.data[DOMAIN][config.entry_id][COORDINATOR],
        async_add_entities=async_add_entities,
    )


class MySkodaBinarySensor(MySkodaEntity, BinarySensorEntity):
    pass


class AirConditioningBinarySensor(MySkodaBinarySensor):
    def _air_conditioning(self) -> AirConditioning:
        air_conditioning = self.vehicle.air_conditioning
        if air_conditioning is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )
        return air_conditioning

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AIR_CONDITIONING]


class StatusBinarySensor(MySkodaBinarySensor):
    def _status(self) -> Status:
        status = self.vehicle.status
        if status is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )
        return status

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE]


class ChargerConnected(AirConditioningBinarySensor):
    """Detects if the charger is connected to the car."""

    entity_description = BinarySensorEntityDescription(
        key="charger_connected",
        name="Charger Connected",
        device_class=BinarySensorDeviceClass.PLUG,
        translation_key="charger_connected",
    )

    @property
    def is_on(self):  # noqa: D102
        return (
            self._air_conditioning().charger_connection_state
            == common.ConnectionState.CONNECTED
        )

    @property
    def icon(self):  # noqa: D102
        if (
            self._air_conditioning().charger_connection_state
            == common.ConnectionState.CONNECTED
        ):
            return "mdi:power-plug"
        return "mdi:power-plug-off"


class ChargerLocked(AirConditioningBinarySensor):
    """Detect if the charger is locked on the car, or whether it can be unplugged."""

    entity_description = BinarySensorEntityDescription(
        key="charger_locked",
        name="Charger",
        device_class=BinarySensorDeviceClass.LOCK,
        translation_key="charger_locked",
    )

    @property
    def is_on(self):  # noqa: D102
        return (
            self._air_conditioning().charger_lock_state
            != common.ChargerLockedState.LOCKED
        )

    @property
    def icon(self):  # noqa: D102
        if (
            self._air_conditioning().charger_lock_state
            == common.ChargerLockedState.LOCKED
        ):
            return "mdi:lock"
        return "mdi:lock-open"


class Locked(StatusBinarySensor):
    """Detects whether the vehicle is fully locked."""

    entity_description = BinarySensorEntityDescription(
        key="locked",
        name="Locks",
        device_class=BinarySensorDeviceClass.LOCK,
        translation_key="locked",
    )

    @property
    def is_on(self):  # noqa: D102
        return not self._status().overall.locked == DoorLockedState.UNLOCKED

    @property
    def icon(self):  # noqa: D102
        if self.is_on:
            return "mdi:lock-open"
        return "mdi:lock"


class DoorsLocked(StatusBinarySensor):
    """Detect whether the doors are locked."""

    entity_description = BinarySensorEntityDescription(
        key="doors_locked",
        name="Doors Locks",
        device_class=BinarySensorDeviceClass.LOCK,
        translation_key="doors_locked",
    )

    @property
    def is_on(self):  # noqa: D102
        return not self._status().overall.doors_locked == DoorLockedState.UNLOCKED

    @property
    def icon(self):  # noqa: D102
        if self.is_on:
            return "mdi:car-door-lock-open"
        return "mdi:car-door-lock"


class DoorsOpen(StatusBinarySensor):
    """Detects whether at least one door is open."""

    entity_description = BinarySensorEntityDescription(
        key="doors_open",
        name="Doors",
        device_class=BinarySensorDeviceClass.DOOR,
        icon="mdi:car-door",
        translation_key="doors_open",
    )

    @property
    def is_on(self):  # noqa: D102
        return self._status().overall.doors == OpenState.OPEN


class WindowsOpen(StatusBinarySensor):
    """Detects whether at least one window is open."""

    entity_description = BinarySensorEntityDescription(
        key="windows_open",
        name="Windows",
        device_class=BinarySensorDeviceClass.WINDOW,
        icon="mdi:car-door",
        translation_key="windows_open",
    )

    @property
    def is_on(self):  # noqa: D102
        return self._status().overall.windows == OpenState.OPEN


class TrunkOpen(StatusBinarySensor):
    """Detects whether the trunk is open."""

    entity_description = BinarySensorEntityDescription(
        key="trunk_open",
        name="Trunk",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:car",
        translation_key="trunk_open",
    )

    @property
    def is_on(self):  # noqa: D102
        return self._status().detail.trunk == OpenState.OPEN


class BonnetOpen(StatusBinarySensor):
    """Detects whether the bonnet is open."""

    entity_description = BinarySensorEntityDescription(
        key="bonnet_open",
        name="Bonnet",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:car",
        translation_key="bonnet_open",
    )

    @property
    def is_on(self):  # noqa: D102
        return self._status().detail.bonnet == OpenState.OPEN


class SunroofOpen(StatusBinarySensor):
    """Detects whether the sunroof is open."""

    entity_description = BinarySensorEntityDescription(
        key="sunroof_open",
        name="Sunroof",
        device_class=BinarySensorDeviceClass.OPENING,
        icon="mdi:car-select",
    )

    @property
    def is_on(self):  # noqa: D102
        return self._status().detail.sunroof == OpenState.OPEN

    def is_supported(self) -> bool:
        return (
            super().is_supported()
            and self._status().detail.sunroof != OpenState.UNSUPPORTED
        )


class LightsOn(StatusBinarySensor):
    """Detects whether the lights are on."""

    entity_description = BinarySensorEntityDescription(
        key="lights_on",
        name="Lights",
        device_class=BinarySensorDeviceClass.LIGHT,
        icon="mdi:car-light-high",
        translation_key="lights_on",
    )

    @property
    def is_on(self):  # noqa: D102
        return self._status().overall.lights == OnOffState.ON
