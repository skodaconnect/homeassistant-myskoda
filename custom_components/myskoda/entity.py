"""MySkoda Entity base classes."""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from myskoda import Vehicle
from myskoda.models.info import CapabilityId

from .const import DOMAIN
from .coordinator import MySkodaDataUpdateCoordinator


class MySkodaEntity(CoordinatorEntity):
    """Base class for all entities in the MySkoda integration."""

    vin: str
    coordinator: MySkodaDataUpdateCoordinator

    def __init__(
        self,
        coordinator: MySkodaDataUpdateCoordinator,
        vin: str,
    ) -> None:  # noqa: D107
        super().__init__(coordinator)
        self.vin = vin
        self.coordinator = coordinator
        self._attr_unique_id = f"{vin}_{self.entity_description.key}"

    @property
    def vehicle(self) -> Vehicle:
        return self.coordinator.data.vehicle

    @property
    def device_info(self) -> DeviceInfo:  # noqa: D102
        return {
            "identifiers": {(DOMAIN, self.vehicle.info.vin)},
            "name": self.vehicle.info.specification.title,
            "manufacturer": "Škoda",
            "serial_number": self.vehicle.info.vin,
            "sw_version": self.vehicle.info.software_version,
            "hw_version": f"{self.vehicle.info.specification.system_model_id}-{self.vehicle.info.specification.model_year}",
            "model": self.vehicle.info.specification.model,
        }

    def required_capabilities(self) -> list[CapabilityId]:
        return []

    def is_supported(self) -> bool:
        return all(
            self.vehicle.has_capability(cap) for cap in self.required_capabilities()
        )
