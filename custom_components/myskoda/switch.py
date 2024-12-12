"""Switches for the MySkoda integration."""

import logging
from datetime import timedelta

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]
from homeassistant.util import Throttle

from myskoda.models.charging import (
    Charging,
    ChargingState,
    ChargingStatus,
    MaxChargeCurrent,
    Settings,
)
from myskoda.models.air_conditioning import (
    AirConditioningAtUnlock,
    AirConditioningWithoutExternalPower,
    SeatHeating,
    WindowHeating,
)
from myskoda.models.common import ActiveState, OnOffState
from myskoda.models.info import CapabilityId
from myskoda.mqtt import OperationFailedError

from .const import API_COOLDOWN_IN_SECONDS, CONF_READONLY, COORDINATORS, DOMAIN
from .entity import MySkodaEntity
from .utils import add_supported_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    add_supported_entities(
        available_entities=[
            WindowHeatingSwitch,
            EnableCharging,
            ReducedCurrent,
            BatteryCareMode,
            AcAtUnlock,
            AcWithoutExternalPower,
            AcSeatHeatingFrontLeft,
            AcSeatHeatingFrontRight,
            AcWindowHeating,
        ],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaSwitch(MySkodaEntity, SwitchEntity):
    """Base class for all switches in the MySkoda integration."""

    def is_supported(self) -> bool:
        all_capabilities_present = all(
            self.vehicle.has_capability(cap) for cap in self.required_capabilities()
        )
        readonly = self.coordinator.config.options.get(CONF_READONLY)

        return all_capabilities_present and not readonly


class WindowHeatingSwitch(MySkodaSwitch):
    """Controls window heating."""

    entity_description = SwitchEntityDescription(
        key="window_heating",
        name="Window Heating",
        device_class=SwitchDeviceClass.SWITCH,
        translation_key="window_heating",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if ac := self.vehicle.air_conditioning:
            return (
                ac.window_heating_state.front == OnOffState.ON
                or ac.window_heating_state.rear == OnOffState.ON
            )

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_turn_on_off(self, turn_on: bool, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        try:
            if turn_on:
                await self.coordinator.myskoda.start_window_heating(
                    self.vehicle.info.vin
                )
            else:
                await self.coordinator.myskoda.stop_window_heating(
                    self.vehicle.info.vin
                )
        except OperationFailedError as exc:
            _LOGGER.error("Failed to stop window heating: %s", exc)

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=False)
        _LOGGER.debug("Window heating disabled.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=True)
        _LOGGER.debug("Window heating enabled.")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.WINDOW_HEATING]


class ChargingSwitch(MySkodaSwitch):
    """Shows charging."""

    entity_description = SwitchEntityDescription(
        key="charging_switch",
        name="Charging",
        device_class=SwitchDeviceClass.SWITCH,
        translation_key="charging_switch",
    )

    def _charging(self) -> Charging | None:
        if charging := self.vehicle.charging:
            return charging

    def _settings(self) -> Settings | None:
        if charging := self._charging():
            if settings := charging.settings:
                return settings

    def _status(self) -> ChargingStatus | None:
        if charging := self._charging():
            return charging.status

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING]


class BatteryCareMode(ChargingSwitch):
    """Controls battery care mode."""

    entity_description = SwitchEntityDescription(
        key="battery_care_mode",
        name="Battery Care Mode",
        device_class=SwitchDeviceClass.SWITCH,
        translation_key="battery_care_mode",
        entity_category=EntityCategory.CONFIG,
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if settings := self._settings():
            return settings.charging_care_mode == ActiveState.ACTIVATED

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_turn_on_off(self, turn_on: bool, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        try:
            if turn_on:
                await self.coordinator.myskoda.set_battery_care_mode(
                    self.vehicle.info.vin, True
                )
            else:
                await self.coordinator.myskoda.set_battery_care_mode(
                    self.vehicle.info.vin, False
                )
        except OperationFailedError as exc:
            _LOGGER.error("Failed to set battery care: %s", exc)

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=False)
        _LOGGER.info("Battery care mode disabled.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=True)
        _LOGGER.info("Battery care mode enabled.")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.BATTERY_CHARGING_CARE]


class ReducedCurrent(ChargingSwitch):
    """Control whether to charge with reduced current."""

    entity_description = SwitchEntityDescription(
        key="reduced_current",
        name="Reduced Current",
        device_class=SwitchDeviceClass.SWITCH,
        translation_key="reduced_current",
        entity_category=EntityCategory.CONFIG,
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if settings := self._settings():
            return settings.max_charge_current_ac == MaxChargeCurrent.REDUCED

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_turn_on_off(self, turn_on: bool, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        try:
            if turn_on:
                await self.coordinator.myskoda.set_reduced_current_limit(
                    self.vehicle.info.vin, True
                )
            else:
                await self.coordinator.myskoda.set_reduced_current_limit(
                    self.vehicle.info.vin, False
                )
        except OperationFailedError as exc:
            _LOGGER.error("Failed to set current limit: %s", exc)

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=False)
        _LOGGER.info("Reduced current limit disabled.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=True)
        _LOGGER.info("Reduced current limit enabled.")


class EnableCharging(ChargingSwitch):
    """Control whether the vehicle should be charging."""

    entity_description = SwitchEntityDescription(
        key="charging",
        name="Charging",
        device_class=SwitchDeviceClass.SWITCH,
        translation_key="charging",
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if status := self._status():
            return status.state == ChargingState.CHARGING

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_turn_on_off(self, turn_on: bool, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        try:
            if turn_on:
                await self.coordinator.myskoda.start_charging(self.vehicle.info.vin)
            else:
                await self.coordinator.myskoda.stop_charging(self.vehicle.info.vin)
        except OperationFailedError as exc:
            _LOGGER.error("Failed to switch charging: %s", exc)

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=False)
        _LOGGER.info("Charging stopped.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=True)
        _LOGGER.info("Charging started.")


class AcAtUnlock(MySkodaSwitch):
    """Enable/disable climatisation when unlocked"""

    entity_description = SwitchEntityDescription(
        key="ac_at_unlock",
        name="AC when Unlocked",
        device_class=SwitchDeviceClass.SWITCH,
        translation_key="ac_at_unlock",
        entity_category=EntityCategory.CONFIG,
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if ac := self.vehicle.air_conditioning:
            if ac.air_conditioning_at_unlock is not None:
                return ac.air_conditioning_at_unlock

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_turn_on_off(self, turn_on: bool, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        settings = AirConditioningAtUnlock(air_conditioning_at_unlock_enabled=turn_on)
        try:
            if turn_on:
                await self.coordinator.myskoda.set_ac_at_unlock(
                    self.vehicle.info.vin, settings
                )
            else:
                await self.coordinator.myskoda.set_ac_at_unlock(
                    self.vehicle.info.vin, settings
                )
        except OperationFailedError as exc:
            _LOGGER.error("Failed to set AC unlock setting: %s", exc)

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=False)
        _LOGGER.info("AC at Unlock deactivated.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=True)
        _LOGGER.info("AC at Unlock activated.")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AIR_CONDITIONING_SMART_SETTINGS]


class AcWithoutExternalPower(MySkodaSwitch):
    """Enable/disable climatisation without external power"""

    entity_description = SwitchEntityDescription(
        key="ac_without_external_power",
        name="AC without External Power",
        device_class=SwitchDeviceClass.SWITCH,
        translation_key="ac_without_external_power",
        entity_category=EntityCategory.CONFIG,
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if ac := self.vehicle.air_conditioning:
            if ac.air_conditioning_without_external_power is not None:
                return ac.air_conditioning_without_external_power

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_turn_on_off(self, turn_on: bool, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        settings = AirConditioningWithoutExternalPower(
            air_conditioning_without_external_power_enabled=turn_on
        )
        try:
            if turn_on:
                await self.coordinator.myskoda.set_ac_without_external_power(
                    self.vehicle.info.vin, settings
                )
            else:
                await self.coordinator.myskoda.set_ac_without_external_power(
                    self.vehicle.info.vin, settings
                )
        except OperationFailedError as exc:
            _LOGGER.error("Failed to change AC without external power: %s", exc)

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=False)
        _LOGGER.info("AC without external power deactivated.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=True)
        _LOGGER.info("AC without external power activated.")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_ELECTRIC]


class AcSeatHeatingFrontLeft(MySkodaSwitch):
    """Enable/disable front left seat heating during climatisation."""

    entity_description = SwitchEntityDescription(
        key="ac_seat_heating_front_left",
        name="Front Left Seat Heating with AC",
        device_class=SwitchDeviceClass.SWITCH,
        translation_key="ac_seat_heating_front_left",
        entity_category=EntityCategory.CONFIG,
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if (
            (ac := self.vehicle.air_conditioning)
            and ac.seat_heating_activated
            and ac.seat_heating_activated.front_left is not None
        ):
            return ac.seat_heating_activated.front_left

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_turn_on_off(self, turn_on: bool, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        settings = SeatHeating(front_left=turn_on)
        try:
            if turn_on:
                await self.coordinator.myskoda.set_seats_heating(
                    self.vehicle.info.vin, settings
                )
            else:
                await self.coordinator.myskoda.set_seats_heating(
                    self.vehicle.info.vin, settings
                )
        except OperationFailedError as exc:
            _LOGGER.error("Failed to change seat heating: %s", exc)

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=False)
        _LOGGER.info("FrontLeft seat heating with AC deactivated.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=True)
        _LOGGER.info("FrontLeft seat heating with AC activated.")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AIR_CONDITIONING_SMART_SETTINGS]


class AcSeatHeatingFrontRight(MySkodaSwitch):
    """Enable/disable front right seat heating during climatisation."""

    entity_description = SwitchEntityDescription(
        key="ac_seat_heating_front_right",
        name="Front Right Seat Heating with AC",
        device_class=SwitchDeviceClass.SWITCH,
        translation_key="ac_seat_heating_front_right",
        entity_category=EntityCategory.CONFIG,
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if (
            (ac := self.vehicle.air_conditioning)
            and ac.seat_heating_activated
            and ac.seat_heating_activated.front_right is not None
        ):
            return ac.seat_heating_activated.front_right

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_turn_on_off(self, turn_on: bool, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        settings = SeatHeating(front_right=turn_on)
        try:
            if turn_on:
                await self.coordinator.myskoda.set_seats_heating(
                    self.vehicle.info.vin, settings
                )
            else:
                await self.coordinator.myskoda.set_seats_heating(
                    self.vehicle.info.vin, settings
                )
        except OperationFailedError as exc:
            _LOGGER.error("Failed to change seat heating: %s", exc)

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=False)
        _LOGGER.info("FrontLeft seat heating with AC deactivated.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=True)
        _LOGGER.info("FrontLeft seat heating with AC activated.")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AIR_CONDITIONING_SMART_SETTINGS]


class AcWindowHeating(MySkodaSwitch):
    """Enable/disable window heating during climatisation."""

    entity_description = SwitchEntityDescription(
        key="ac_window_heating",
        name="Window Heating with AC",
        device_class=SwitchDeviceClass.SWITCH,
        translation_key="ac_window_heating",
        entity_category=EntityCategory.CONFIG,
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if ac := self.vehicle.air_conditioning:
            if ac.window_heating_enabled is not None:
                return ac.window_heating_enabled

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_turn_on_off(self, turn_on: bool, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        settings = WindowHeating(window_heating_enabled=turn_on)
        try:
            if turn_on:
                await self.coordinator.myskoda.set_windows_heating(
                    self.vehicle.info.vin, settings
                )
            else:
                await self.coordinator.myskoda.set_windows_heating(
                    self.vehicle.info.vin, settings
                )
        except OperationFailedError as exc:
            _LOGGER.error("Failed to set window heating: %s", exc)

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=False)
        _LOGGER.info("Window heating with AC deactivated.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=True)
        _LOGGER.info("Window heating with AC activated.")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AIR_CONDITIONING_SMART_SETTINGS]
