"""Button entities for MySkoda."""

import logging
from datetime import timedelta
from typing import Coroutine

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]
from homeassistant.util import Throttle

from myskoda.models.info import CapabilityId
from myskoda.mqtt import OperationFailedError

from .const import API_COOLDOWN_IN_SECONDS, CONF_READONLY, COORDINATORS, DOMAIN
from .coordinator import MySkodaConfigEntry, MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity
from .utils import add_supported_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: MySkodaConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the button platform."""
    add_supported_entities(
        available_entities=[HonkFlash, Flash, WakeUp],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaButton(MySkodaEntity, ButtonEntity):
    """Button Entity.

    Base class for all button entities in the MySkoda integration.
    """

    def __init__(self, coordinator: MySkodaDataUpdateCoordinator, vin: str):
        super().__init__(coordinator, vin)
        self._is_enabled: bool = True

    def is_supported(self) -> bool:
        all_capabilities_present = all(
            self.vehicle.has_capability(cap) for cap in self.required_capabilities()
        )
        readonly = self.coordinator.entry.options.get(CONF_READONLY)

        return all_capabilities_present and not readonly

    def _disable_button(self):
        self._is_enabled = False
        self.async_write_ha_state()

    def _enable_button(self):
        self._is_enabled = True
        self.async_write_ha_state()

    async def _press_button(self, to_call: Coroutine):
        """Press a button by executing to_call."""

        if not self._is_enabled:
            return

        self._disable_button()
        try:
            await to_call
        finally:
            self._enable_button()

    @property
    def available(self) -> bool:
        """Return whether the button is available to be pressed."""
        return self._is_enabled


class HonkFlash(MySkodaButton):
    """Honk and Flash."""

    entity_description = ButtonEntityDescription(
        key="honk_flash",
        translation_key="honk_flash",
        device_class=ButtonDeviceClass.IDENTIFY,
    )

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_press(self) -> None:
        if not self._is_enabled:
            return  # Ignore presses when disabled

        myskoda, vin = self.coordinator.myskoda, self.vehicle.info.vin
        try:
            await self._press_button(myskoda.honk_flash(vin))
        except OperationFailedError as exc:
            _LOGGER.error("Failed honk and flash: %s", exc)
        _LOGGER.info("Sent honk and flash")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.HONK_AND_FLASH]


class Flash(MySkodaButton):
    """Flash."""

    entity_description = ButtonEntityDescription(
        key="flash", translation_key="flash", device_class=ButtonDeviceClass.IDENTIFY
    )

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_press(self) -> None:
        if not self._is_enabled:
            return  # Ignore presses when disabled

        myskoda, vin = self.coordinator.myskoda, self.vehicle.info.vin
        try:
            await self._press_button(myskoda.flash(vin))
        except OperationFailedError as exc:
            _LOGGER.error("Failed to flash lights: %s", exc)
        _LOGGER.info("Sent light flash")

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.HONK_AND_FLASH]


class WakeUp(MySkodaButton):
    """Explicitly wake up the vehicle.

    Disabled by default to limit accidental use.
    """

    entity_description = ButtonEntityDescription(
        key="wakeup",
        translation_key="wakeup",
        device_class=ButtonDeviceClass.RESTART,
        entity_registry_enabled_default=False,
    )

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_press(self) -> None:
        if not self._is_enabled:
            return

        myskoda, vin = self.coordinator.myskoda, self.vehicle.info.vin
        try:
            await self._press_button(myskoda.wakeup(vin))
        except OperationFailedError as exc:
            _LOGGER.error("Failed to wake up vehicle: %s", exc)
        _LOGGER.info("Signaled vehicle to wake up")

    def is_supported(self) -> bool:
        """Some models have VEHICLE_WAKE_UP while others have VEHICLE_WAKE_UP_TRIGGER."""
        capabilities = [
            CapabilityId.VEHICLE_WAKE_UP,
            CapabilityId.VEHICLE_WAKE_UP_TRIGGER,
        ]
        return any(self.vehicle.has_capability(cap) for cap in capabilities)
