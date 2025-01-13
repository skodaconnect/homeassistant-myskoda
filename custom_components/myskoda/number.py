"""Number entities for MySkoda."""

import logging
from datetime import timedelta

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]
from homeassistant.util import Throttle

from myskoda.models.info import CapabilityId
from myskoda.mqtt import OperationFailedError

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
        available_entities=[ChargeLimit, AuxiliaryHeaterDuration],
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
        readonly = self.coordinator.entry.options.get(CONF_READONLY)

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
        try:
            await self.coordinator.myskoda.set_charge_limit(
                self.vehicle.info.vin, int(value)
            )
        except OperationFailedError as exc:
            _LOGGER.error("Failed to set charging limit: %s", exc)

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING]

    def forbidden_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING_MQB]


class AuxiliaryHeaterDuration(MySkodaNumber, RestoreEntity):
    """Auxiliary heater timer."""

    entity_description = NumberEntityDescription(
        key="auxiliary_heater_duration",
        mode=NumberMode.SLIDER,
        native_max_value=60,
        native_min_value=5,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_step=5,
        translation_key="auxiliary_heater_duration",
        entity_category=EntityCategory.CONFIG,
    )

    _attr_native_value: float = 15  # Default value

    def __init__(self, coordinator, vehicle_id):
        """Initialize the auxiliary heater timer."""
        super().__init__(coordinator, vehicle_id)

    @property
    def native_value(self) -> float | None:
        """Return the current value of the timer."""
        return self.coordinator.data.config.auxiliary_heater_duration

    async def async_set_native_value(self, value: float) -> None:
        """Asynchronously update the current value."""
        self.coordinator.data.config.auxiliary_heater_duration = value
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle entity which is added to Home Assistant."""
        await super().async_added_to_hass()

        # Attempt to restore the previous state
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                restored_value = float(last_state.state)
                # Restore the coordinator duration from the last known state
                self.coordinator.data.config.auxiliary_heater_duration = restored_value
            except ValueError:
                # If error, use the default value
                self.coordinator.data.config.auxiliary_heater_duration = (
                    self._attr_native_value
                )
        else:
            # If no state to restore, use the default value
            self.coordinator.data.config.auxiliary_heater_duration = (
                self._attr_native_value
            )

        # Update HA state to reflect the restored value
        self.async_write_ha_state()

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AUXILIARY_HEATING]

    def forbidden_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AUXILIARY_HEATING_TEMPERATURE_SETTING]
