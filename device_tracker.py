"""Device Tracker entities for MySkoda."""

from typing import overload

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DATA_COODINATOR, DOMAIN
from .entity import MySkodaDataEntity
from .myskoda import Vehicle


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config.entry_id][DATA_COODINATOR]

    vehicles = coordinator.data

    entities = [DeviceTracker(coordinator, vehicle) for vehicle in vehicles]

    async_add_entities(entities, update_before_add=True)


class DeviceTracker(MySkodaDataEntity, TrackerEntity):
    """GPS device tracker for MySkoda."""

    vehicle: Vehicle

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            EntityDescription(
                name=vehicle.info.title,
                key=f"{vehicle.info.vin}_device_tracker",
            ),
        )

    @property
    @overload
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    @overload
    def latitude(self) -> float | None:
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.position.lat

    @property
    @overload
    def longitude(self) -> float | None:
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.position.lng
