"""Climate entities for MySkoda."""

from asyncio import sleep
import logging

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
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from myskoda import Vehicle

from .const import DATA_COODINATOR, DOMAIN
from .entity import MySkodaDataEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config.entry_id][DATA_COODINATOR]

    vehicles = coordinator.data.get("vehicles")

    entities = [MySkodaClimate(coordinator, vehicle) for vehicle in vehicles]

    async_add_entities(entities, update_before_add=True)


class MySkodaClimate(MySkodaDataEntity, ClimateEntity):
    """Climate control for MySkoda vehicles."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            ClimateEntityDescription(
                key="climate",
                name=f"{vehicle.info.specification.title} Air Conditioning",
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
    def hvac_modes(self) -> list[HVACMode]:  # noqa: D102
        return [HVACMode.AUTO, HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode | None:  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        if self.vehicle.air_conditioning.state:
            return HVACMode.AUTO
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        if self.vehicle.air_conditioning.state == "HEATING":
            return HVACAction.HEATING
        if self.vehicle.air_conditioning.state == "COOLING":
            return HVACAction.COOLING
        return HVACAction.OFF

    @property
    def target_temperature(self) -> None | float:  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.air_conditioning.target_temperature.temperature_value

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):  # noqa: D102
        if hvac_mode == HVACMode.AUTO:
            await self.coordinator.hub.start_air_conditioning(
                self.vehicle.info.vin,
                self.vehicle.air_conditioning.target_temperature.temperature_value,
            )
        else:
            await self.coordinator.hub.stop_air_conditioning(self.vehicle.info.vin)
        for _ in range(10):
            await sleep(15)
            if self.hvac_mode == hvac_mode:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("HVAC mode set to %s.", hvac_mode)

    async def async_turn_on(self):  # noqa: D102
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self):  # noqa: D102
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs):  # noqa: D102
        temp = kwargs[ATTR_TEMPERATURE]
        await self.coordinator.hub.set_target_temperature(self.vehicle.info.vin, temp)
        for _ in range(10):
            await sleep(15)
            if self.target_temperature == temp:
                break
            await self.coordinator.async_refresh()
        _LOGGER.info("AC disabled.")
