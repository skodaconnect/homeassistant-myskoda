"""Number entities for MySkoda."""

import logging
from datetime import timedelta

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]
from homeassistant.util import Throttle

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
        available_entities=[ChargeLimit],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaNumber(MySkodaEntity, NumberEntity):
    """Number Entity.

    Base class for all number entities in the MySkoda integration.
    """

    def is_supported(self) -> bool:
        all_capabilities_present = all(
            self.vehicle.has_capability(cap) for cap in self.required_capabilities()
        )
        readonly = self.coordinator.config.options.get(CONF_READONLY)

        return all_capabilities_present and not readonly


class ChargeLimit(MySkodaNumber):
    """Charge limit.

    Represents the maximum value in percent that the car can be charged to.
    """

    entity_description = NumberEntityDescription(
        key="charge_limit",
        native_max_value=100,
        native_min_value=50,
        native_unit_of_measurement=PERCENTAGE,
        native_step=10,
        translation_key="charge_limit",
        entity_category=EntityCategory.CONFIG,
    )

    _attr_device_class = NumberDeviceClass.BATTERY

    @property
    def native_value(self) -> float | None:  # noqa: D102
        if charging := self.vehicle.charging:
            if settings := charging.settings:
                return settings.target_state_of_charge_in_percent

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_set_native_value(self, value: float):  # noqa: D102
        await self.coordinator.myskoda.set_charge_limit(
            self.vehicle.info.vin, int(value)
        )

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING]

    def forbidden_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING_MQB]
