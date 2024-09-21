"""Number entities for MySkoda."""

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
from myskoda.models.charging import Settings
from myskoda.models.info import CapabilityId

from .const import COORDINATORS, DOMAIN
from .entity import MySkodaEntity
from .utils import InvalidCapabilityConfigurationError, add_supported_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    add_supported_entities(
        available_entities=[ChargeLimit],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaNumber(MySkodaEntity, NumberEntity):
    """Number Entity.

    Base class for all number entities in the MySkoda integration.
    """

    pass


class ChargeLimit(MySkodaNumber):
    """Charge limit.

    Represents the maximum value in percent that the car can be charged to.
    """

    entity_description = NumberEntityDescription(
        key="charge_limit",
        name="Charge Limit",
        icon="mdi:battery-lock",
        native_max_value=100,
        native_min_value=50,
        native_unit_of_measurement=PERCENTAGE,
        native_step=10,
        translation_key="charge_limit",
    )

    _attr_device_class = NumberDeviceClass.BATTERY

    def _settings(self) -> Settings:
        if self.vehicle.charging is None or self.vehicle.charging.settings is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )

        return self.vehicle.charging.settings

    @property
    def native_value(self) -> float | None:  # noqa: D102
        return self._settings().target_state_of_charge_in_percent

    async def async_set_native_value(self, value: float):  # noqa: D102
        await self.coordinator.myskoda.set_charge_limit(
            self.vehicle.info.vin, int(value)
        )

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING]
