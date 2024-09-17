"""Number entities for Enyaq."""

from asyncio import sleep
import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
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

    entities = [ChargeLimit(coordinator, vehicle) for vehicle in vehicles]

    async_add_entities(entities, update_before_add=True)


class MySkodaNumber(MySkodaDataEntity, NumberEntity):
    """Number Entity.

    Base class for all number entities in the MySkoda integration.
    """

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        vehicle: Vehicle,
        entity_description: NumberEntityDescription,
    ) -> None:
        """Create new Number."""

        super().__init__(coordinator, vehicle, entity_description)
        NumberEntity.__init__(self)


class ChargeLimit(MySkodaNumber):
    """Charge limit.

    Represents the maximum value in percent that the car can be charged to.
    """

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        """Create new ChargeLimit."""

        super().__init__(
            coordinator,
            vehicle,
            NumberEntityDescription(
                key="charge_limit",
                name=f"{vehicle.info.specification.title} Charge Limit",
                icon="mdi:battery-lock",
                native_max_value=100,
                native_min_value=50,
                native_unit_of_measurement=PERCENTAGE,
                native_step=10,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_charge_limit"
        self._attr_device_class = NumberDeviceClass.BATTERY

    @property
    def native_value(self) -> float | None:  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.settings.target_state_of_charge_in_percent

    async def async_set_native_value(self, value: float):  # noqa: D102
        await self.coordinator.hub.set_charge_limit(self.vehicle.info.vin, value)
        for _ in range(10):
            await sleep(15)
            if self.native_value == value:
                break
            await self.coordinator.async_refresh()
        _LOGGER.debug("Changed charge limit to %s.", value)
