"""MySkoda Entity base classes."""

from homeassistant.helpers.entity import DeviceInfo, Entity, EntityDescription
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from myskoda import Vehicle

from .const import DOMAIN


class MySkodaEntity(Entity):
    """Base class for all entities in the MySkoda integration."""

    vehicle: Vehicle

    def __init__(self, vehicle: Vehicle, entity_description: EntityDescription) -> None:  # noqa: D107
        super().__init__()
        self.vehicle = vehicle
        self.entity_description = entity_description

    @property
    def device_info(self) -> DeviceInfo:  # noqa: D102
        return {
            "identifiers": {(DOMAIN, self.vehicle.info.vin)},
            "name": self.vehicle.info.title,
            "manufacturer": "Škoda",
            "sw_version": self.vehicle.info.software_version,
            "hw_version": f"{self.vehicle.info.model_id}-{self.vehicle.info.model_year}",
            "model": self.vehicle.info.model,
        }


class MySkodaDataEntity(CoordinatorEntity, MySkodaEntity):
    """Base class for all entities that need to access data from the coordinator."""

    def __init__(  # noqa: D107
        self,
        coordinator: DataUpdateCoordinator,
        vehicle: Vehicle,
        entity_description: EntityDescription,
    ) -> None:
        super().__init__(coordinator)
        MySkodaEntity.__init__(self, vehicle, entity_description)

    def _update_device_from_coordinator(self) -> None:
        for vehicle in self.coordinator.data.get("vehicles"):
            if vehicle.info.vin == self.vehicle.info.vin:
                self.vehicle = vehicle
                return
