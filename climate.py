"""Enyaq Climate."""

from asyncio import sleep
import logging

from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    HVACMode,
    HVACAction,
    ClimateEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .entity import EnyaqDataEntity, EnyaqEntity
from .enyaq import EnyaqHub, Vehicle
from .const import DATA_COODINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)


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
        entities.append(EnyaqClimate(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class EnyaqClimate(EnyaqDataEntity, ClimateEntity):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(
            coordinator,
            vehicle,
            ClimateEntityDescription(
                key="climate",
                name=f"{vehicle.info.title} Air Conditioning",
                icon="mdi:air-conditioner",
            ),
        )
        ClimateEntity.__init__(self)
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        self._attr_unique_id = f"{self.vehicle.info.vin}_climate"

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return [HVACMode.AUTO, HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode | None:
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        if self.vehicle.air_conditioning.air_conditioning_on:
            return HVACMode.AUTO
        else:
            return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        if self.vehicle.air_conditioning.state == "HEATING":
            return HVACAction.HEATING
        elif self.vehicle.air_conditioning.state == "COOLING":
            return HVACAction.COOLING
        elif self.vehicle.air_conditioning.state == "OFF":
            return HVACAction.OFF

    @property
    def target_temperature(self) -> None | float:
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.air_conditioning.target_temperature_celsius

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        if hvac_mode == HVACMode.AUTO:
            await self.coordinator.hub.start_air_conditioning(
                self.vehicle.info.vin,
                self.vehicle.air_conditioning.target_temperature_celsius,
            )
        else:
            await self.coordinator.hub.stop_air_conditioning(self.vehicle.info.vin)
        for i in range(0, 10):
            await sleep(15)
            if self.hvac_mode == hvac_mode:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info(f"HVAC mode set to {hvac_mode}.")

    async def async_turn_on(self):
        await self.set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self):
        await self.set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs):
        temp = kwargs[ATTR_TEMPERATURE]
        await self.coordinator.hub.set_target_temperature(self.vehicle.info.vin, temp)
        for i in range(0, 10):
            await sleep(15)
            if self.target_temperature == temp:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("AC disabled.")

