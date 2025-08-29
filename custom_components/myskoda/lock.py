"""Locks for the MySkoda integration."""

import logging
from datetime import timedelta
from typing import Coroutine

from homeassistant.components.lock import (
    LockEntity,
    LockEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]
from homeassistant.util import Throttle

from myskoda.models.common import DoorLockedState
from myskoda.models.info import CapabilityId
from myskoda.mqtt import OperationFailedError

from .const import API_COOLDOWN_IN_SECONDS, COORDINATORS, CONF_SPIN, DOMAIN
from .coordinator import MySkodaConfigEntry
from .entity import MySkodaEntity
from .utils import add_supported_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: MySkodaConfigEntry,
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

    def __init__(self, coordinator, vin):
        super().__init__(coordinator, vin)
        self._is_enabled: bool = True
        if not self.coordinator.entry.options.get(CONF_SPIN):
            self._is_enabled = False

    def _disable_lock(self):
        self._is_enabled = False
        self.async_write_ha_state()

    def _enable_lock(self):
        self._is_enabled = True
        self.async_write_ha_state()

    async def _operate_lock(self, to_call: Coroutine):
        """Operate lock by executing to_call."""
        if not self._is_enabled:
            return

        self._disable_lock()
        try:
            await to_call
        finally:
            self._enable_lock()

    @property
    def available(self) -> bool:
        return self._is_enabled


class DoorLock(MySkodaLock):
    """Central door lock."""

    entity_description = LockEntityDescription(
        key="door_lock",
        translation_key="door_lock",
    )

    @property
    def is_locked(self) -> bool | None:
        if status := self.vehicle.status:
            return status.overall.doors_locked == DoorLockedState.LOCKED

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def _async_lock_unlock(self, lock: bool, spin: str, **kwargs):  # noqa: D102
        """Internal method to have a central location for the Throttle."""
        if not self._is_enabled:
            return

        myskoda, vin = self.coordinator.myskoda, self.vehicle.info.vin
        try:
            if lock:
                await self._operate_lock(myskoda.lock(vin, spin))
            else:
                await self._operate_lock(myskoda.unlock(vin, spin))
        except OperationFailedError as exc:
            _LOGGER.error("Failed to unlock vehicle: %s", exc)

    async def async_lock(self, **kwargs) -> None:
        entry_options = self.coordinator.entry.options
        if entry_options.get(CONF_SPIN):
            await self._async_lock_unlock(lock=True, spin=entry_options.get(CONF_SPIN))
            _LOGGER.info("Sent command to lock the vehicle.")
        else:
            _LOGGER.error("Cannot lock car: No S-PIN set.")
            raise ServiceValidationError("no_spin")

    async def async_unlock(self, **kwargs) -> None:
        entry_options = self.coordinator.entry.options
        if entry_options.get(CONF_SPIN):
            await self._async_lock_unlock(lock=False, spin=entry_options.get(CONF_SPIN))
            _LOGGER.info("Sent command to unlock the vehicle.")
        else:
            _LOGGER.error("Cannot unlock car: No S-PIN set.")
            raise ServiceValidationError("no_spin")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.ACCESS]
