"""Locks for the MySkoda integration."""

import logging
from datetime import timedelta

from homeassistant.components.lock import (
    LockEntity,
    LockEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]
from homeassistant.util import Throttle

from myskoda.models.common import DoorLockedState
from myskoda.models.info import CapabilityId
from myskoda.mqtt import OperationFailedError

from .const import API_COOLDOWN_IN_SECONDS, COORDINATORS, CONF_SPIN, DOMAIN
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
            DoorLock,
        ],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaLock(MySkodaEntity, LockEntity):
    """Base class for all locks in the MySkoda integration."""

    pass


class DoorLock(MySkodaLock):
    """Central door lock."""

    entity_description = LockEntityDescription(
        key="door_lock",
        translation_key="door_lock",
    )

    @property
    def available(self) -> bool:
        if not self.coordinator.entry.options.get(CONF_SPIN):
            return False
        return True

    @property
    def is_locked(self) -> bool | None:
        if status := self.vehicle.status:
            return status.overall.doors_locked == DoorLockedState.LOCKED

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_lock_unlock(self, lock: bool, spin: str, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        try:
            if lock:
                await self.coordinator.myskoda.lock(self.vehicle.info.vin, spin)
            else:
                await self.coordinator.myskoda.unlock(self.vehicle.info.vin, spin)
        except OperationFailedError as exc:
            _LOGGER.error("Failed to unlock vehicle: %s", exc)

    async def async_lock(self, **kwargs) -> None:
        if self.coordinator.entry.options.get(CONF_SPIN):
            await self._async_lock_unlock(
                lock=True, spin=self.coordinator.entry.options.get(CONF_SPIN)
            )
            _LOGGER.info("Sent command to lock the vehicle.")
        else:
            _LOGGER.error("Cannot lock car: No S-PIN set.")

    async def async_unlock(self, **kwargs) -> None:
        if self.coordinator.entry.options.get(CONF_SPIN):
            await self._async_lock_unlock(
                lock=False, spin=self.coordinator.entry.options.get(CONF_SPIN)
            )
            _LOGGER.info("Sent command to unlock the vehicle.")
        else:
            _LOGGER.error("Cannot unlock car: No S-PIN set.")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.ACCESS]
