"""Climate entities for MySkoda."""

import logging
from datetime import timedelta

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]
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
    AuxiliaryState,
    AuxiliaryStartMode,
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
from .coordinator import MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity
from .utils import add_supported_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    add_supported_entities(
        available_entities=[MySkodaClimate, AuxiliaryHeater],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaClimate(MySkodaEntity, ClimateEntity):
    """Climate control for MySkoda vehicles."""

    entity_description = ClimateEntityDescription(
        key="climate",
        translation_key="climate",
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: MySkodaDataUpdateCoordinator, vin: str) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vin,
        )
        ClimateEntity.__init__(self)

    def _air_conditioning(self) -> AirConditioning | None:
        return self.vehicle.air_conditioning

    @property
    def hvac_modes(self) -> list[HVACMode]:  # noqa: D102
        return [HVACMode.HEAT_COOL, HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode | None:  # noqa: D102
        if ac := self._air_conditioning():
            if (
                ac.state != AirConditioningState.OFF
                and ac.state != AirConditioningState.HEATING_AUXILIARY
            ):
                return HVACMode.HEAT_COOL
            return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:  # noqa: D102
        if ac := self._air_conditioning():
            if ac.state == "HEATING":
                return HVACAction.HEATING
            if ac.state == "COOLING":
                return HVACAction.COOLING
            return HVACAction.OFF

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature that can be set."""
        return 15.5  # Restrict to a minimum of 15.5°C

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature that can be set."""
        return 30.0  # Restrict to a maximum of 30°C

    @property
    def target_temperature(self) -> None | float:  # noqa: D102
        if ac := self._air_conditioning():
            target_temperature = ac.target_temperature
            if target_temperature is None:
                return
            return target_temperature.temperature_value

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_set_hvac_mode(self, hvac_mode: HVACMode):  # noqa: D102
        if ac := self._air_conditioning():
            target_temperature = ac.target_temperature
            if target_temperature is None:
                return

            if hvac_mode == HVACMode.HEAT_COOL:
                if ac.state == AirConditioningState.HEATING_AUXILIARY:
                    _LOGGER.info("Auxiliary heating detected, stopping first.")
                    try:
                        await self.coordinator.myskoda.stop_auxiliary_heating(
                            self.vehicle.info.vin
                        )
                    except OperationFailedError as exc:
                        _LOGGER.error(
                            "Failed to stop aux heater, aborting action: %s", exc
                        )
                        return
                _LOGGER.info("Starting Air conditioning.")
                try:
                    await self.coordinator.myskoda.start_air_conditioning(
                        self.vehicle.info.vin,
                        target_temperature.temperature_value,
                    )
                except OperationFailedError as exc:
                    _LOGGER.error("Failed to start air conditioning: %s", exc)
            else:
                _LOGGER.info("Stopping Air conditioning.")
                try:
                    await self.coordinator.myskoda.stop_air_conditioning(
                        self.vehicle.info.vin
                    )
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
        try:
            await self.coordinator.myskoda.set_target_temperature(
                self.vehicle.info.vin, temp
            )
            _LOGGER.info("Target temperature for AC set to %s.", temp)
        except OperationFailedError as exc:
            _LOGGER.error("Failed to set AC target temperature: %s", exc)

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AIR_CONDITIONING]

    def is_supported(self) -> bool:
        all_capabilities_present = all(
            self.vehicle.has_capability(cap) for cap in self.required_capabilities()
        )
        readonly = self.coordinator.config.options.get(CONF_READONLY)

        return all_capabilities_present and not readonly


class AuxiliaryHeater(MySkodaEntity, ClimateEntity):
    """Auxiliary heater control for MySkoda vehicles."""

    entity_description = ClimateEntityDescription(
        key="auxiliary_heater",
        translation_key="auxiliary_heater",
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: MySkodaDataUpdateCoordinator, vin: str) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vin,
        )
        ClimateEntity.__init__(self)

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

    def _air_conditioning(self) -> AirConditioning | None:
        return self.vehicle.air_conditioning

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
    def available(self) -> bool:  # noqa: D102
        if not self.coordinator.config.options.get(CONF_SPIN):
            return False
        return True

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
        if state := self._state:
            if state == AuxiliaryState.HEATING_AUXILIARY:
                return HVACMode.HEAT
            if state == AuxiliaryState.VENTILATION:
                return HVACMode.FAN_ONLY
            return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:  # noqa: D102
        if state := self._state:
            if state == AuxiliaryState.HEATING_AUXILIARY:
                return HVACAction.HEATING
            if state == AuxiliaryState.VENTILATION:
                return HVACAction.FAN
            return HVACAction.OFF

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature that can be set."""
        return 15.5  # Restrict to a minimum of 15.5°C

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature that can be set."""
        return 30.0  # Restrict to a maximum of 30°C

    @property
    def target_temperature(self) -> None | float:  # noqa: D102
        if target_temperature := self._target_temperature:
            return target_temperature.temperature_value

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_set_hvac_mode(self, hvac_mode: HVACMode):  # noqa: D102
        if state := self._state:

            async def handle_mode(desired_state, start_mode=None, **kwargs):
                if state == desired_state:
                    _LOGGER.info("%s already running.", state)
                    return

                if state != AirConditioningState.OFF:
                    _LOGGER.info("%s mode detected, stopping first.", state)
                    try:
                        await self.coordinator.myskoda.stop_air_conditioning(
                            self.vehicle.info.vin
                        )
                    except OperationFailedError as exc:
                        _LOGGER.error("Failed to stop air conditioning: %s", exc)
                        return

                config = AuxiliaryConfig(
                    duration_in_seconds=self._duration_in_seconds,
                    start_mode=start_mode,
                    **kwargs,
                )
                spin = self.coordinator.config.options.get(CONF_SPIN)
                if spin is None:
                    _LOGGER.error("Cannot start %s: No S-PIN set.", desired_state)
                    return

                _LOGGER.info("Starting %s [%s]", start_mode or "heating", config)
                try:
                    await self.coordinator.myskoda.start_auxiliary_heating(
                        vin=self.vehicle.info.vin,
                        spin=spin,
                        config=config,
                    )
                except OperationFailedError as exc:
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
                        await self.coordinator.myskoda.stop_auxiliary_heating(
                            self.vehicle.info.vin
                        )
                    except OperationFailedError as exc:
                        _LOGGER.error("Failed to stop aux heater: %s", exc)

            _LOGGER.info("Auxiliary HVAC mode set to %s.", hvac_mode)
        else:
            _LOGGER.error("Can't retrieve air-conditioning info")

    async def async_turn_on(self):  # noqa: D102
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):  # noqa: D102
        await self.async_set_hvac_mode(HVACMode.OFF)

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_set_temperature(self, **kwargs):  # noqa: D102
        temp = kwargs[ATTR_TEMPERATURE]
        if temp is not None:
            # Ensure the temperature stays within range
            if temp < self.min_temp:
                temp = self.min_temp
            elif temp > self.max_temp:
                temp = self.max_temp
        try:
            await self.coordinator.myskoda.set_target_temperature(
                self.vehicle.info.vin, temp
            )
            _LOGGER.info("Target temperature for auxiliary heater set to %s.", temp)
        except OperationFailedError as exc:
            _LOGGER.error("Failed to set aux heater temperature: %s", exc)

    def is_supported(self) -> bool:
        """Return true if any supported capability is present."""
        return self.has_any_capability(
            [
                CapabilityId.AUXILIARY_HEATING,
                CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_AUXILIARY,
            ]
        )
