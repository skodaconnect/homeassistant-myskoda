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
from myskoda.models.auxiliary_heating import AuxiliaryConfig, AuxiliaryStartMode
from myskoda.models.info import CapabilityId

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
        return 16.0  # Restrict to a minimum of 16°C

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
                    await self.coordinator.myskoda.stop_auxiliary_heating(
                        self.vehicle.info.vin
                    )
                _LOGGER.info("Starting Air conditioning.")
                await self.coordinator.myskoda.start_air_conditioning(
                    self.vehicle.info.vin,
                    target_temperature.temperature_value,
                )
            else:
                _LOGGER.info("Stopping Air conditioning.")
                await self.coordinator.myskoda.stop_air_conditioning(
                    self.vehicle.info.vin
                )
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
        await self.coordinator.myskoda.set_target_temperature(
            self.vehicle.info.vin, temp
        )
        _LOGGER.info("Target temperature for AC set to %s.", temp)

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

        if self.vehicle.has_capability(
            CapabilityId.AUXILIARY_HEATING_TEMPERATURE_SETTING
        ) or self.vehicle.has_capability(
            CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_AUXILIARY
        ):
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE

    def _has_any_capability(self, cap: list[CapabilityId]) -> bool:
        """Check if any capabilities in the list is supported."""
        return any(self.vehicle.has_capability(capability) for capability in cap)

    def _has_capability(self, cap: list[CapabilityId]) -> bool:
        """Check if all capabilities in the list are supported."""
        return all(self.vehicle.has_capability(capability) for capability in cap)

    def _air_conditioning(self) -> AirConditioning | None:
        return self.vehicle.air_conditioning

    @property
    def _target_temperature(self) -> TargetTemperature | None:
        """Return target temp object for auxiliary heater."""
        if self._has_any_capability(
            [
                CapabilityId.AUXILIARY_HEATING_TEMPERATURE_SETTING,
                CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_AUXILIARY,
            ]
        ):
            if ac := self._air_conditioning():
                target_temperature = ac.target_temperature
                if target_temperature is not None:
                    return target_temperature
        return None

    @property
    def _heater_source(self) -> HeaterSource | None:
        """Return heater source for auxiliary heater."""
        if self._has_capability(
            [CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_AUXILIARY]
        ):
            return HeaterSource.AUTOMATIC
        return None

    @property
    def _start_mode(self) -> AuxiliaryStartMode | None:
        """Return start mode for auxiliary heater."""
        if self._has_capability(
            [CapabilityId.AUXILIARY_HEATING, CapabilityId.ACTIVE_VENTILATION]
        ):
            return AuxiliaryStartMode.HEATING
        return None

    @property
    def _duration_in_seconds(self) -> int | None:
        """Return duration formated to seconds."""
        if not self._has_any_capability(
            [
                CapabilityId.AUXILIARY_HEATING_TEMPERATURE_SETTING,
                CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_AUXILIARY,
            ]
        ):
            duration = self.coordinator.duration
            if duration is not None:
                return int(duration) * 60
        return None

    @property
    def available(self) -> bool:  # noqa: D102
        if not self.coordinator.config.options.get(CONF_SPIN):
            return False
        return True

    @property
    def hvac_modes(self) -> list[HVACMode]:  # noqa: D102
        modes = [HVACMode.HEAT, HVACMode.OFF]
        if self._has_capability([CapabilityId.ACTIVE_VENTILATION]):
            modes.append(HVACMode.FAN_ONLY)
        return modes

    @property
    def hvac_mode(self) -> HVACMode | None:  # noqa: D102
        if ac := self._air_conditioning():
            if ac.state == AirConditioningState.HEATING_AUXILIARY:
                return HVACMode.HEAT
            if ac.state == AirConditioningState.VENTILATION:
                return HVACMode.FAN_ONLY
            return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:  # noqa: D102
        if ac := self._air_conditioning():
            if ac.state == AirConditioningState.HEATING_AUXILIARY:
                return HVACAction.HEATING
            if ac.state == AirConditioningState.VENTILATION:
                return HVACAction.FAN
            return HVACAction.OFF

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature that can be set."""
        return 16.0  # Restrict to a minimum of 16°C

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
            if hvac_mode == HVACMode.HEAT:
                spin = self.coordinator.config.options.get(CONF_SPIN)
                if spin is not None:
                    if (
                        ac.state != AirConditioningState.OFF
                        and ac.state != AirConditioningState.HEATING_AUXILIARY
                    ):
                        _LOGGER.info("%s mode detected, stopping first.", ac.state)
                        await self.coordinator.myskoda.stop_air_conditioning(
                            self.vehicle.info.vin
                        )
                    if ac.state == AirConditioningState.HEATING_AUXILIARY:
                        _LOGGER.info("%s already running.", ac.state)
                        return

                    config = AuxiliaryConfig(
                        target_temperature=self._target_temperature,
                        duration_in_seconds=self._duration_in_seconds,
                        start_mode=self._start_mode,
                        heater_source=self._heater_source,
                    )
                    _LOGGER.info("Starting Auxiliary heating [%s]", config)

                    await self.coordinator.myskoda.start_auxiliary_heating(
                        vin=self.vehicle.info.vin, spin=spin, config=config
                    )
                else:
                    _LOGGER.error("Cannot start auxiliary heater: No S-PIN set.")
            elif hvac_mode == HVACMode.FAN_ONLY:
                spin = self.coordinator.config.options.get(CONF_SPIN)
                if spin is not None:
                    if (
                        ac.state != AirConditioningState.OFF
                        and ac.state != AirConditioningState.VENTILATION
                    ):
                        _LOGGER.info("%s mode detected, stopping first.", ac.state)
                        await self.coordinator.myskoda.stop_air_conditioning(
                            self.vehicle.info.vin
                        )
                    if ac.state == AirConditioningState.VENTILATION:
                        _LOGGER.info("%s already running.", ac.state)
                        return

                    config = AuxiliaryConfig(
                        duration_in_seconds=self._duration_in_seconds,
                        start_mode=AuxiliaryStartMode.VENTILATION,
                    )
                    # TODO check if some other mode is not running
                    _LOGGER.info("Starting ventilation [%s]", config)
                else:
                    _LOGGER.error("Cannot start ventilation: No S-PIN set.")
            else:
                if ac.state == AirConditioningState.OFF:
                    _LOGGER.info("Auxiliary heater already OFF.")
                    return

                _LOGGER.info("Stopping Auxiliary heater.")
                await self.coordinator.myskoda.stop_auxiliary_heating(
                    self.vehicle.info.vin
                )
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
        await self.coordinator.myskoda.set_target_temperature(
            self.vehicle.info.vin, temp
        )
        _LOGGER.info("Target temperature for auxiliary heater set to %s.", temp)

    def is_supported(self) -> bool:
        """Return true if any supported capability is present."""
        if self.vehicle.has_capability(
            CapabilityId.AUXILIARY_HEATING
        ) or self.vehicle.has_capability(
            CapabilityId.AIR_CONDITIONING_HEATING_SOURCE_AUXILIARY
        ):
            return True
        else:
            return False
