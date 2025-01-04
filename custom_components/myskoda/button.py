"""Button entities for MySkoda."""

import logging
from datetime import timedelta

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.components.persistent_notification import (
    async_create as async_create_persistent_notification,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]
from homeassistant.util import Throttle

from myskoda.models.fixtures import Endpoint
from myskoda.models.info import CapabilityId
from myskoda.mqtt import OperationFailedError

from .const import API_COOLDOWN_IN_SECONDS, CONF_READONLY, COORDINATORS, DOMAIN
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
    """Set up the button platform."""
    add_supported_entities(
        available_entities=[HonkFlash, Flash, GenerateFixtures],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaButton(MySkodaEntity, ButtonEntity):
    """Button Entity.

    Base class for all button entities in the MySkoda integration.
    """

    def is_supported(self) -> bool:
        all_capabilities_present = all(
            self.vehicle.has_capability(cap) for cap in self.required_capabilities()
        )
        readonly = self.coordinator.entry.options.get(CONF_READONLY)

        return all_capabilities_present and not readonly


class HonkFlash(MySkodaButton):
    """Honk and Flash."""

    entity_description = ButtonEntityDescription(
        key="honk_flash",
        translation_key="honk_flash",
        device_class=ButtonDeviceClass.IDENTIFY,
    )

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_press(self) -> None:
        try:
            await self.coordinator.myskoda.honk_flash(self.vehicle.info.vin)
        except OperationFailedError as exc:
            _LOGGER.error("Failed honk and flash: %s", exc)

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.HONK_AND_FLASH]


class Flash(MySkodaButton):
    """Flash."""

    entity_description = ButtonEntityDescription(
        key="flash", translation_key="flash", device_class=ButtonDeviceClass.IDENTIFY
    )

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_press(self) -> None:
        try:
            await self.coordinator.myskoda.flash(self.vehicle.info.vin)
        except OperationFailedError as exc:
            _LOGGER.error("Failed to flash lights: %s", exc)

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.HONK_AND_FLASH]


class GenerateFixtures(MySkodaButton):
    """Generate Fixtures.
    This entity is deprecated and disabled by default, scheduled to be removed in v2.0.0

    The functionality is implemented in the 'Diagnostics' function for the HA device,
    which is where it should be.
    """

    entity_description = ButtonEntityDescription(
        key="generate_fixtures",
        translation_key="generate_fixtures",
        device_class=ButtonDeviceClass.IDENTIFY,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        entity_registry_visible_default=False,
    )

    def __init__(
        self,
        coordinator: MySkodaDataUpdateCoordinator,
        vin: str,
    ):
        super().__init__(coordinator, vin)
        self._is_enabled = True  # Track whether the button is enabled

    @property
    def available(self) -> bool:
        """Return whether the button is available."""
        return self._is_enabled

    @Throttle(timedelta(seconds=API_COOLDOWN_IN_SECONDS))
    async def async_press(self) -> None:
        if not self._is_enabled:
            return  # Ignore presses when disabled

        # Disable the button
        self._is_enabled = False
        self.async_write_ha_state()

        try:
            vin: list[str] = [self.vehicle.info.vin]
            description = f"Fixtures for {self.vehicle.info.specification.model} {self.vehicle.info.specification.trim_level} {self.vehicle.info.specification.model_year}"

            result = await self.coordinator.myskoda.generate_get_fixture(
                self.vehicle.info.specification.model, description, vin, Endpoint.ALL
            )
            _LOGGER.info(f"{description}: {result.to_json()}")

            async_create_persistent_notification(
                self.hass,
                title="Fixtures Generated",
                message=f"{description} has been successfully generated, check the log.",
            )
        finally:
            # Re-enable the button
            self._is_enabled = True
            self.async_write_ha_state()
