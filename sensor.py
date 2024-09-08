"""Oilfox metering."""

from pickle import TRUE

from .enyaq import EnyaqHub, Vehicle
from .const import DATA_COODINATOR, DOMAIN
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
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
    
    await coordinator.hub.authenticate(config.data["email"], config.data["password"]);

    vehicle = coordinator.data

    entities = []

    entities.append(EnyaqSensorSoftwareVersion(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class EnyaqSensor(CoordinatorEntity, SensorEntity):
    hub: EnyaqHub
    vehicle: Vehicle

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(coordinator)

        self.vehicle = vehicle

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self.vehicle.vin)},
            "name": self.vehicle.title,
            "manufacturer": "Škoda",
        }

    def _update_device_from_coordinator(self) -> None:
        self.vehicle = self.coordinator.data

class EnyaqSensorSoftwareVersion(EnyaqSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(coordinator, vehicle)

        self._attr_name = f"{self.vehicle.title} Software Version"
        self._attr_unique_id = f"{self.vehicle.vin}_software_version"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:update"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.vehicle.software_version