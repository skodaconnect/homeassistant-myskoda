"""Oilfox metering."""

from pickle import TRUE

from homeassistant.components.device_tracker.const import SourceType

from .entity import EnyaqDataEntity

from .enyaq import EnyaqHub, Vehicle
from .const import DATA_COODINATOR, DOMAIN
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""\
    
    coordinator = hass.data[DOMAIN][config.entry_id][DATA_COODINATOR]

    vehicles = coordinator.data

    entities = []

    for vehicle in vehicles:
        entities.append(EnyaqSensorDeviceTracker(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class EnyaqSensorDeviceTracker(EnyaqDataEntity, TrackerEntity):
    hub: EnyaqHub
    vehicle: Vehicle

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(coordinator, vehicle, EntityDescription(
            name = vehicle.info.title,
            key = f"{vehicle.info.vin}_device_tracker",
        ))

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.vehicle.position.lat

    @property
    def longitude(self) -> float | None:
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.vehicle.position.lng