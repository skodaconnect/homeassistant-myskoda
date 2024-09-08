"""Oilfox metering."""

from pickle import TRUE

from homeassistant.components.device_tracker.const import SourceType

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


class EnyaqSensorDeviceTracker(CoordinatorEntity, TrackerEntity):
    hub: EnyaqHub
    vehicle: Vehicle

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(coordinator)
        self.vehicle = vehicle
        self._attr_name = self.vehicle.info.title

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self.vehicle.info.vin)},
            "name": self.vehicle.info.title,
            "manufacturer": "Škoda",
            "sw_version": self.vehicle.info.software_version,
            "hw_version": f"{self.vehicle.info.model_id}-{self.vehicle.info.model_year}",
            "model": self.vehicle.info.model,
        }

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


    def _update_device_from_coordinator(self) -> None:
        for vehicle in self.coordinator.data:
            if vehicle.info.vin == self.vehicle.info.vin:
                self.vehicle = vehicle
                return