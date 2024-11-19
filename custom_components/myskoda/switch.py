"""Switches for the MySkoda integration."""

import logging
from datetime import timedelta

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
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
from myskoda.models.common import ActiveState, OnOffState
from myskoda.models.info import CapabilityId

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
            WindowHeating,
            EnableCharging,
            ReducedCurrent,
            BatteryCareMode,
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


class WindowHeating(MySkodaSwitch):
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
        if turn_on:
            await self.coordinator.myskoda.start_window_heating(self.vehicle.info.vin)
        else:
            await self.coordinator.myskoda.stop_window_heating(self.vehicle.info.vin)

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
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if settings := self._settings():
            return settings.charging_care_mode == ActiveState.ACTIVATED

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_turn_on_off(self, turn_on: bool, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        if turn_on:
            await self.coordinator.myskoda.set_battery_care_mode(
                self.vehicle.info.vin, True
            )
        else:
            await self.coordinator.myskoda.set_reduced_current_limit(
                self.vehicle.info.vin, False
            )

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
    )

    @property
    def is_on(self) -> bool | None:  # noqa: D102
        if settings := self._settings():
            return settings.max_charge_current_ac == MaxChargeCurrent.REDUCED

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_turn_on_off(self, turn_on: bool, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        if turn_on:
            await self.coordinator.myskoda.set_reduced_current_limit(
                self.vehicle.info.vin, True
            )
        else:
            await self.coordinator.myskoda.set_reduced_current_limit(
                self.vehicle.info.vin, False
            )

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
        if turn_on:
            await self.coordinator.myskoda.start_charging(self.vehicle.info.vin)
        else:
            await self.coordinator.myskoda.stop_charging(self.vehicle.info.vin)

    async def async_turn_off(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=False)
        _LOGGER.info("Charging stopped.")

    async def async_turn_on(self, **kwargs):  # noqa: D102
        await self._async_turn_on_off(turn_on=True)
        _LOGGER.info("Charging started.")
