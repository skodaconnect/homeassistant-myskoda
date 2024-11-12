"""Button entities for MySkoda."""

import logging
from datetime import timedelta

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]
from homeassistant.util import Throttle

from myskoda.models.info import CapabilityId

from .const import API_COOLDOWN_IN_SECONDS, COORDINATORS, DOMAIN
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
        available_entities=[Honk, Flash],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaButton(MySkodaEntity, ButtonEntity):
    """Button Entity.

    Base class for all button entities in the MySkoda integration.
    """

    pass


class Honk(MySkodaButton):
    """Honk."""

    entity_description = ButtonEntityDescription(
        key="honk",
        translation_key="honk",
        device_class=ButtonDeviceClass.IDENTIFY
    )

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_press(self) -> None:
        await self.coordinator.myskoda.honk_flash(self.vehicle.info.vin, True)

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.HONK_AND_FLASH]


class Flash(MySkodaButton):
    """Flash."""

    entity_description = ButtonEntityDescription(
        key="flash",
        translation_key="flash",
        device_class=ButtonDeviceClass.IDENTIFY
    )

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_press(self) -> None:
        await self.coordinator.myskoda.honk_flash(self.vehicle.info.vin, False)

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.HONK_AND_FLASH]
