"""Enyaq Entity."""

from homeassistant.helpers.entity import Entity, DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .enyaq import Vehicle
from .const import DOMAIN

class EnyaqEntity(Entity):
    vehicle: Vehicle

    def __init__(self, vehicle: Vehicle, entity_description: EntityDescription) -> None:
        super().__init__()
        self.vehicle = vehicle
        self.entity_description = entity_description

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


class EnyaqDataEntity(CoordinatorEntity, EnyaqEntity):
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        vehicle: Vehicle,
        entity_description: EntityDescription,
    ) -> None:
        super().__init__(coordinator)
        EnyaqEntity.__init__(self, vehicle, entity_description)

    def _update_device_from_coordinator(self) -> None:
        for vehicle in self.coordinator.data:
            if vehicle.info.vin == self.vehicle.info.vin:
                self.vehicle = vehicle
                return
