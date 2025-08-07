"""Binary Sensors for MySkoda."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]

from myskoda import common
from myskoda.models.air_conditioning import AirConditioning
from myskoda.models.common import (
    DoorLockedState,
    OnOffState,
    OpenState,
    ChargerLockedState,
)
from myskoda.models.info import CapabilityId
from myskoda.models.status import DoorWindowState, Status
from myskoda.models.vehicle_connection_status import VehicleConnectionStatus

from .const import COORDINATORS, DOMAIN
from .coordinator import MySkodaConfigEntry
from .entity import MySkodaEntity
from .utils import add_supported_entities


async def async_setup_entry(
    hass: HomeAssistant,
    config: MySkodaConfigEntry,
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
            ParkingLightsOn,
            ChargerConnected,
            ChargerLocked,
            SunroofOpen,
            DoorOpenFrontLeft,
            DoorOpenFrontRight,
            DoorOpenRearLeft,
            DoorOpenRearRight,
            WindowOpenFrontLeft,
            WindowOpenFrontRight,
            WindowOpenRearLeft,
            WindowOpenRearRight,
            VehicleBatteryProtection,
            VehicleInMotion,
            VehicleReachable,
        ],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaBinarySensor(MySkodaEntity, BinarySensorEntity):
    pass


class AirConditioningBinarySensor(MySkodaBinarySensor):
    def _air_conditioning(self) -> AirConditioning | None:
        return self.vehicle.air_conditioning

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AIR_CONDITIONING]


class StatusBinarySensor(MySkodaBinarySensor):
    def _status(self) -> Status | None:
        return self.vehicle.status

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE]


class VehicleConnectionBinarySensor(MySkodaBinarySensor):
    def _connection_status(self) -> VehicleConnectionStatus | None:
        return self.vehicle.connection_status

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.READINESS]


class ChargerConnected(AirConditioningBinarySensor):
    """Detects if the charger is connected to the car."""

    entity_description = BinarySensorEntityDescription(
        key="charger_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        translation_key="charger_connected",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if ac := self._air_conditioning():
            return ac.charger_connection_state == common.ConnectionState.CONNECTED


class ChargerLocked(AirConditioningBinarySensor):
    """Detect if the charger is locked on the car, or whether it can be unplugged."""

    entity_description = BinarySensorEntityDescription(
        key="charger_lock",
        device_class=BinarySensorDeviceClass.LOCK,
        translation_key="charger_lock",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if ac := self._air_conditioning():
            if ac.charger_lock_state != ChargerLockedState.INVALID:
                return ac.charger_lock_state != common.ChargerLockedState.LOCKED


class Locked(StatusBinarySensor):
    """Detects whether the vehicle is fully locked."""

    # Keep in mind, a lock that is open, is "ON" for HomeAssistant

    entity_description = BinarySensorEntityDescription(
        key="vehicle_lock",
        device_class=BinarySensorDeviceClass.LOCK,
        translation_key="vehicle_lock",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return not status.overall.locked == DoorLockedState.LOCKED


class DoorsLocked(StatusBinarySensor):
    """Detect whether the doors are locked."""

    entity_description = BinarySensorEntityDescription(
        key="doors_lock",
        device_class=BinarySensorDeviceClass.LOCK,
        translation_key="doors_lock",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return not status.overall.doors_locked == DoorLockedState.LOCKED


class DoorsOpen(StatusBinarySensor):
    """Detects whether at least one door is open."""

    entity_description = BinarySensorEntityDescription(
        key="doors_open",
        device_class=BinarySensorDeviceClass.DOOR,
        translation_key="doors_open",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return status.overall.doors == OpenState.OPEN


class WindowsOpen(StatusBinarySensor):
    """Detects whether at least one window is open."""

    entity_description = BinarySensorEntityDescription(
        key="windows_open",
        device_class=BinarySensorDeviceClass.WINDOW,
        translation_key="windows_open",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return status.overall.windows == OpenState.OPEN


class TrunkOpen(StatusBinarySensor):
    """Detects whether the trunk is open."""

    entity_description = BinarySensorEntityDescription(
        key="trunk_open",
        device_class=BinarySensorDeviceClass.OPENING,
        translation_key="trunk_open",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return status.detail.trunk == OpenState.OPEN


class BonnetOpen(StatusBinarySensor):
    """Detects whether the bonnet is open."""

    entity_description = BinarySensorEntityDescription(
        key="bonnet_open",
        device_class=BinarySensorDeviceClass.OPENING,
        translation_key="bonnet_open",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return status.detail.bonnet == OpenState.OPEN


class SunroofOpen(StatusBinarySensor):
    """Detects whether the sunroof is open."""

    entity_description = BinarySensorEntityDescription(
        key="sunroof_open",
        device_class=BinarySensorDeviceClass.OPENING,
        translation_key="sunroof_open",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            if (
                status.detail.sunroof is None
                or status.detail.sunroof == OpenState.UNSUPPORTED
            ):
                return
            return status.detail.sunroof == OpenState.OPEN

    @property
    def available(self) -> bool:
        if status := self._status():
            return (
                super().is_supported()
                and status.detail.sunroof != OpenState.UNSUPPORTED
            )
        return False


class ParkingLightsOn(StatusBinarySensor):
    """Detects whether the parking-lights are on."""

    entity_description = BinarySensorEntityDescription(
        key="lights_on",
        device_class=BinarySensorDeviceClass.LIGHT,
        translation_key="parkinglights_on",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return status.overall.lights == OnOffState.ON


class DoorOpenFrontLeft(StatusBinarySensor):
    """Left front door status."""

    entity_description = BinarySensorEntityDescription(
        key="door_open_front_left",
        device_class=BinarySensorDeviceClass.DOOR,
        translation_key="door_open_front_left",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return status.left_front_door in {
                DoorWindowState.DOOR_OPEN,
                DoorWindowState.ALL_OPEN,
            }


class DoorOpenFrontRight(StatusBinarySensor):
    """Right front door status."""

    entity_description = BinarySensorEntityDescription(
        key="door_open_front_right",
        device_class=BinarySensorDeviceClass.DOOR,
        translation_key="door_open_front_right",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return status.right_front_door in {
                DoorWindowState.DOOR_OPEN,
                DoorWindowState.ALL_OPEN,
            }


class DoorOpenRearLeft(StatusBinarySensor):
    """Left rear door status."""

    entity_description = BinarySensorEntityDescription(
        key="door_open_rear_left",
        device_class=BinarySensorDeviceClass.DOOR,
        translation_key="door_open_rear_left",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return status.left_back_door in {
                DoorWindowState.DOOR_OPEN,
                DoorWindowState.ALL_OPEN,
            }


class DoorOpenRearRight(StatusBinarySensor):
    """Right rear door status."""

    entity_description = BinarySensorEntityDescription(
        key="door_open_rear_right",
        device_class=BinarySensorDeviceClass.DOOR,
        translation_key="door_open_rear_right",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return status.right_back_door in {
                DoorWindowState.DOOR_OPEN,
                DoorWindowState.ALL_OPEN,
            }


class WindowOpenFrontLeft(StatusBinarySensor):
    """Left front window status."""

    entity_description = BinarySensorEntityDescription(
        key="window_open_front_left",
        device_class=BinarySensorDeviceClass.WINDOW,
        translation_key="window_open_front_left",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return status.left_front_door in {
                DoorWindowState.WINDOW_OPEN,
                DoorWindowState.ALL_OPEN,
            }


class WindowOpenFrontRight(StatusBinarySensor):
    """Right front window status."""

    entity_description = BinarySensorEntityDescription(
        key="window_open_front_right",
        device_class=BinarySensorDeviceClass.WINDOW,
        translation_key="window_open_front_right",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            if status.right_front_door == DoorWindowState.UNKNOWN:
                return None
            return status.right_front_door in {
                DoorWindowState.WINDOW_OPEN,
                DoorWindowState.ALL_OPEN,
            }


class WindowOpenRearLeft(StatusBinarySensor):
    """Left rear window status."""

    entity_description = BinarySensorEntityDescription(
        key="window_open_rear_left",
        device_class=BinarySensorDeviceClass.WINDOW,
        translation_key="window_open_rear_left",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            if status.left_back_door == DoorWindowState.UNKNOWN:
                return None
            return status.left_back_door in {
                DoorWindowState.WINDOW_OPEN,
                DoorWindowState.ALL_OPEN,
            }


class WindowOpenRearRight(StatusBinarySensor):
    """Right rear door status."""

    entity_description = BinarySensorEntityDescription(
        key="window_open_rear_right",
        device_class=BinarySensorDeviceClass.WINDOW,
        translation_key="window_open_rear_right",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            if status.right_back_door == DoorWindowState.UNKNOWN:
                return None
            return status.right_back_door in {
                DoorWindowState.WINDOW_OPEN,
                DoorWindowState.ALL_OPEN,
            }


class VehicleReachable(VehicleConnectionBinarySensor):
    """Vehicle reachable status."""

    entity_description = BinarySensorEntityDescription(
        key="vehicle_reachable",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        translation_key="vehicle_reachable",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    @property
    def is_on(self) -> bool | None:
        if cs := self._connection_status():
            return not cs.unreachable


class VehicleInMotion(VehicleConnectionBinarySensor):
    """Vehicle in motion status."""

    entity_description = BinarySensorEntityDescription(
        key="vehicle_in_motion",
        device_class=BinarySensorDeviceClass.MOTION,
        translation_key="vehicle_in_motion",
    )

    @property
    def is_on(self) -> bool | None:
        if cs := self._connection_status():
            return cs.in_motion


class VehicleBatteryProtection(VehicleConnectionBinarySensor):
    """Vehicle is in battery protection state."""

    entity_description = BinarySensorEntityDescription(
        key="vehicle_battery_protection",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="vehicle_battery_protection",
    )

    @property
    def is_on(self) -> bool | None:
        if cs := self._connection_status():
            return cs.battery_protection_limit_on
