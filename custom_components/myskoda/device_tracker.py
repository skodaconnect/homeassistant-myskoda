"""Device Tracker entities for MySkoda."""

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from myskoda import Vehicle

from .const import DATA_COODINATOR, DOMAIN
from .entity import MySkodaDataEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config.entry_id][DATA_COODINATOR]

    vehicles = coordinator.data.get("vehicles")

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
                name=vehicle.info.specification.title,
                key=f"{vehicle.info.vin}_device_tracker",
            ),
        )

    @property
    def source_type(self) -> SourceType:  # noqa: D102
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.position.positions[0].gps_coordinates.latitude

    @property
    def longitude(self) -> float | None:  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.position.positions[0].gps_coordinates.longitude
