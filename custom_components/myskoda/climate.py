"""Climate entities for MySkoda."""

import logging
from datetime import timedelta
from enum import StrEnum
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
)
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import (
    DiscoveryInfoType,  # pyright: ignore [reportAttributeAccessIssue]
)
from homeassistant.util import Throttle

from myskoda.models.air_conditioning import (
    AirConditioning,
    AirConditioningState,
    HeaterSource,
    TargetTemperature,
)
from myskoda.models.auxiliary_heating import (
    AuxiliaryConfig,
    AuxiliaryHeating,
    AuxiliaryStartMode,
    AuxiliaryState,
)
from myskoda.models.info import CapabilityId
from myskoda.mqtt import OperationFailedError

from .const import (
    API_COOLDOWN_IN_SECONDS,
    CONF_READONLY,
    CONF_SPIN,
    COORDINATORS,
    DOMAIN,
)
from .coordinator import MySkodaConfigEntry, MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity
from .utils import add_supported_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MySkodaConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    add_supported_entities(
        available_entities=[MySkodaClimate, AuxiliaryHeater],
        coordinators=hass.data[DOMAIN][entry.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class OptimisticAttribute(StrEnum):
    """Enum for trackable optimistic attributes."""

    TARGET_TEMPERATURE = "target_temperature"
    HVAC_MODE = "hvac_mode"
    HVAC_ACTION = "hvac_action"


class MySkodaClimateEntity(MySkodaEntity, ClimateEntity):
    """Base class for all MySkoda Climate entities."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: MySkodaDataUpdateCoordinator, vin: str) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vin,
        )
        ClimateEntity.__init__(self)
        self._operation_in_progress: bool = False
        self._optimistic_data: dict[OptimisticAttribute, Any] = {}

    @property
    def assumed_state(self) -> bool:
        """Return True if any optimistic value is set."""
        return len(self._optimistic_data) > 0

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature that can be set."""
        return 15.5  # Restrict to a minimum of 15.5°C

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature that can be set."""
        return 30.0  # Restrict to a maximum of 30°C

    def _air_conditioning(self) -> AirConditioning | None:
        return self.vehicle.air_conditioning

    def _set_optimistic_data(self, attr: OptimisticAttribute, value: Any):
        self._optimistic_data[attr] = value
        self.async_write_ha_state()

    def _unset_optimistic_data(self, attr: OptimisticAttribute):
        self._optimistic_data.pop(attr, None)
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Clear optimistic values when fresh data arrives and no operation in progress."""
        if not self._operation_in_progress:
            self._optimistic_data = {}
        super()._handle_coordinator_update()

    async def _stop_auxiliary_heating(self) -> None:
        self._operation_in_progress = True
        try:
            await self.coordinator.myskoda.stop_auxiliary_heating(self.vehicle.info.vin)
        finally:
            self._operation_in_progress = False

    async def _start_auxiliary_heating(
        self, spin: str, config: AuxiliaryConfig
    ) -> None:
        self._operation_in_progress = True
        try:
            await self.coordinator.myskoda.start_auxiliary_heating(
                vin=self.vehicle.info.vin,
                spin=spin,
                config=config,
            )
        finally:
            self._operation_in_progress = False

    async def _stop_air_conditioning(self) -> None:
        self._operation_in_progress = True
        try:
            await self.coordinator.myskoda.stop_air_conditioning(self.vehicle.info.vin)
        finally:
            self._operation_in_progress = False

    async def _start_air_conditioning(self, temperature: float) -> None:
        self._operation_in_progress = True
        try:
            await self.coordinator.myskoda.start_air_conditioning(
                self.vehicle.info.vin, temperature
            )
        finally:
            self._operation_in_progress = False

    async def _set_target_temperature(self, temperature: float) -> None:
        self._operation_in_progress = True
        try:
            await self.coordinator.myskoda.set_target_temperature(
                self.vehicle.info.vin, temperature
            )
        finally:
            self._operation_in_progress = False


class MySkodaClimate(MySkodaClimateEntity):
    """Climate control for MySkoda vehicles."""

    entity_description = ClimateEntityDescription(
        key="climate",
        translation_key="climate",
    )
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    @property
    def hvac_modes(self) -> list[HVACMode]:  # noqa: D102
        return [HVACMode.HEAT_COOL, HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode | None:  # noqa: D102
        if hvac_mode := self._optimistic_data.get(OptimisticAttribute.HVAC_MODE):
            return hvac_mode

        if ac := self._air_conditioning():
            if (
                ac.state != AirConditioningState.OFF
                and ac.state != AirConditioningState.HEATING_AUXILIARY
            ):
                return HVACMode.HEAT_COOL
            return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:  # noqa: D102
        if hvac_action := self._optimistic_data.get(OptimisticAttribute.HVAC_ACTION):
            return hvac_action

        if ac := self._air_conditioning():
            if ac.state == "HEATING":
                return HVACAction.HEATING
            if ac.state == "COOLING":
                return HVACAction.COOLING
            return HVACAction.OFF

    @property
    def target_temperature(self) -> None | float:  # noqa: D102
        if target_temperature := self._optimistic_data.get(
            OptimisticAttribute.TARGET_TEMPERATURE
        ):
            return target_temperature

        if ac := self._air_conditioning():
            target_temperature = ac.target_temperature
            if target_temperature is None:
                return
            return target_temperature.temperature_value

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_set_hvac_mode(self, hvac_mode: HVACMode):  # noqa: D102
        if not (ac := self._air_conditioning()):
            return

        if not (target_temperature := ac.target_temperature):
            return

        self._set_optimistic_data(OptimisticAttribute.HVAC_MODE, hvac_mode)
        if hvac_mode == HVACMode.HEAT_COOL:
            if ac.state == AirConditioningState.HEATING_AUXILIARY:
                _LOGGER.info("Auxiliary heating detected, stopping first.")
                try:
                    await self._stop_auxiliary_heating()
                except OperationFailedError as exc:
                    self._unset_optimistic_data(OptimisticAttribute.HVAC_MODE)
                    _LOGGER.error("Failed to stop aux heater, aborting action: %s", exc)
                    return
            _LOGGER.info("Starting Air conditioning.")
            try:
                await self._start_air_conditioning(target_temperature.temperature_value)

            except OperationFailedError as exc:
                self._unset_optimistic_data(OptimisticAttribute.HVAC_MODE)
                _LOGGER.error("Failed to start air conditioning: %s", exc)

        else:
            _LOGGER.info("Stopping Air conditioning.")
            try:
                await self._stop_air_conditioning()
            except OperationFailedError as exc:
                _LOGGER.error("Failed to stop air conditioning: %s", exc)
        _LOGGER.info("HVAC mode set to %s.", hvac_mode)

    async def async_turn_on(self):  # noqa: D102
        await self.async_set_hvac_mode(HVACMode.HEAT_COOL)

    async def async_turn_off(self):  # noqa: D102
        await self.async_set_hvac_mode(HVACMode.OFF)

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_set_temperature(self, **kwargs):  # noqa: D102
        temp = kwargs[ATTR_TEMPERATURE]
        # Ensure the temperature stays within range
        if temp < self.min_temp:
            temp = self.min_temp
        elif temp > self.max_temp:
            temp = self.max_temp

        self._set_optimistic_data(OptimisticAttribute.TARGET_TEMPERATURE, temp)
        try:
            await self._set_target_temperature(temp)
            _LOGGER.info("Target temperature set to %s.", temp)
        except OperationFailedError as exc:
            self._unset_optimistic_data(OptimisticAttribute.TARGET_TEMPERATURE)
            _LOGGER.error("Failed to set target temperature: %s", exc)

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AIR_CONDITIONING]

    def is_supported(self) -> bool:
        all_capabilities_present = all(
            self.vehicle.has_capability(cap) for cap in self.required_capabilities()
        )
        readonly = self.coordinator.entry.options.get(CONF_READONLY)

        return all_capabilities_present and not readonly


class AuxiliaryHeater(MySkodaClimateEntity):
    """Auxiliary heater control for MySkoda vehicles."""

    entity_description = ClimateEntityDescription(
        key="auxiliary_heater",
        translation_key="auxiliary_heater",
    )

    def __init__(self, coordinator: MySkodaDataUpdateCoordinator, vin: str) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vin,
        )
        self._is_enabled: bool = bool(self.coordinator.entry.options.get(CONF_SPIN))
        self._attr_supported_features = (
            ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        )
        if self.has_any_capability(
            [
                CapabilityId.AUXILIARY_HEATING_TEMPERATURE_SETTING,
                CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_AUXILIARY,
            ]
        ):
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE

    def _auxiliary_heating(self) -> AuxiliaryHeating | None:
        return self.vehicle.auxiliary_heating

    @property
    def _target_temperature(self) -> TargetTemperature | None:
        """Return target temp object for auxiliary heater."""
        if self.has_all_capabilities(
            [CapabilityId.AUXILIARY_HEATING_TEMPERATURE_SETTING]
        ):
            if ac := self._auxiliary_heating():
                return ac.target_temperature
        elif self.has_all_capabilities(
            [CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_AUXILIARY]
        ):
            if ac := self._air_conditioning():
                return ac.target_temperature

    @property
    def _heater_source(self) -> HeaterSource | None:
        """Return heater source for auxiliary heater."""
        if self.has_all_capabilities(
            [CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_AUXILIARY]
        ):
            return HeaterSource.AUTOMATIC

    @property
    def _start_mode(self) -> AuxiliaryStartMode | None:
        """Return start mode for auxiliary heater."""
        if self.has_all_capabilities(
            [CapabilityId.AUXILIARY_HEATING]
        ) and self.has_any_capability(
            [CapabilityId.ACTIVE_VENTILATION, CapabilityId.AUXILIARY_HEATING_BASIC]
        ):
            return AuxiliaryStartMode.HEATING

    @property
    def _duration_in_seconds(self) -> int | None:
        """Return duration formated to seconds."""
        if not self.has_any_capability(
            [
                CapabilityId.AUXILIARY_HEATING_TEMPERATURE_SETTING,
                CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_AUXILIARY,
            ]
        ):
            duration = self.coordinator.data.config.auxiliary_heater_duration
            if duration is not None:
                return int(duration) * 60

    @property
    def _state(self) -> str | None:
        state = None
        if self.has_all_capabilities([CapabilityId.AUXILIARY_HEATING]):
            if ac := self._auxiliary_heating():
                state = ac.state
        else:
            if ac := self._air_conditioning():
                state = ac.state
        return state

    @property
    def hvac_modes(self) -> list[HVACMode]:  # noqa: D102
        modes = [HVACMode.HEAT, HVACMode.OFF]
        if self.has_any_capability(
            [CapabilityId.ACTIVE_VENTILATION, CapabilityId.AUXILIARY_HEATING_BASIC]
        ):
            modes.append(HVACMode.FAN_ONLY)
        return modes

    @property
    def hvac_mode(self) -> HVACMode | None:  # noqa: D102
        if hvac_mode := self._optimistic_data.get(OptimisticAttribute.HVAC_MODE):
            return hvac_mode

        if state := self._state:
            if state == AuxiliaryState.HEATING_AUXILIARY:
                return HVACMode.HEAT
            if state == AuxiliaryState.VENTILATION:
                return HVACMode.FAN_ONLY
            return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:  # noqa: D102
        if hvac_action := self._optimistic_data.get(OptimisticAttribute.HVAC_ACTION):
            return hvac_action

        if state := self._state:
            if state == AuxiliaryState.HEATING_AUXILIARY:
                return HVACAction.HEATING
            if state == AuxiliaryState.VENTILATION:
                return HVACAction.FAN
            return HVACAction.OFF

    @property
    def target_temperature(self) -> None | float:  # noqa: D102
        if target_temperature := self._optimistic_data.get(
            OptimisticAttribute.TARGET_TEMPERATURE
        ):
            return target_temperature

        if target_temperature := self._target_temperature:
            return target_temperature.temperature_value

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_set_hvac_mode(self, hvac_mode: HVACMode):  # noqa: D102
        if not (state := self._state):
            _LOGGER.error("Can't retrieve air-conditioning info")
            return

        self._set_optimistic_data(OptimisticAttribute.HVAC_MODE, hvac_mode)

        async def handle_mode(desired_state, start_mode=None, **kwargs):
            if state == desired_state:
                _LOGGER.info("%s already running.", state)
                return

            if state != AirConditioningState.OFF:
                _LOGGER.info("%s mode detected, stopping first.", state)
                try:
                    await self._stop_air_conditioning()
                except OperationFailedError as exc:
                    self._unset_optimistic_data(OptimisticAttribute.HVAC_MODE)
                    _LOGGER.error("Failed to stop air conditioning: %s", exc)
                    return

            config = AuxiliaryConfig(
                duration_in_seconds=self._duration_in_seconds,
                start_mode=start_mode,
                **kwargs,
            )
            spin = self.coordinator.entry.options.get(CONF_SPIN)
            if spin is None:
                self._unset_optimistic_data(OptimisticAttribute.HVAC_MODE)
                _LOGGER.error("Cannot start %s: No S-PIN set.", desired_state)
                return

            _LOGGER.info("Starting %s [%s]", start_mode or "heating", config)
            try:
                await self._start_auxiliary_heating(spin=spin, config=config)
            except OperationFailedError as exc:
                self._unset_optimistic_data(OptimisticAttribute.HVAC_MODE)
                _LOGGER.error("Failed to start aux heating: %s", exc)

        if hvac_mode == HVACMode.HEAT:
            await handle_mode(
                desired_state=AirConditioningState.HEATING_AUXILIARY,
                target_temperature=self._target_temperature,
                start_mode=self._start_mode,
                heater_source=self._heater_source,
            )

        elif hvac_mode == HVACMode.FAN_ONLY:
            await handle_mode(
                desired_state=AirConditioningState.VENTILATION,
                start_mode=AuxiliaryStartMode.VENTILATION,
            )

        else:
            if state == AirConditioningState.OFF:
                _LOGGER.info("Auxiliary heater already OFF.")
            else:
                _LOGGER.info("Stopping Auxiliary heater.")
                try:
                    await self._stop_auxiliary_heating()
                except OperationFailedError as exc:
                    _LOGGER.error("Failed to stop aux heater: %s", exc)

        _LOGGER.info("Auxiliary HVAC mode set to %s.", hvac_mode)

    async def async_turn_on(self):  # noqa: D102
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):  # noqa: D102
        await self.async_set_hvac_mode(HVACMode.OFF)

    def is_supported(self) -> bool:
        """Return true if any supported capability is present."""
        return self.has_any_capability(
            [
                CapabilityId.AUXILIARY_HEATING,
                CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_AUXILIARY,
            ]
        )
