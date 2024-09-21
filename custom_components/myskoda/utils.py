from typing import Callable

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from myskoda import Vehicle

from .coordinator import MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity


def add_supported_entities(
    available_entities: list[
        Callable[[MySkodaDataUpdateCoordinator, str], MySkodaEntity]
    ],
    coordinators: dict[str, MySkodaDataUpdateCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    entities = []

    for vin in coordinators:
        for SensorClass in available_entities:
            sensor = SensorClass(coordinators[vin], vin)
            if sensor.is_supported():
                entities.append(sensor)

    async_add_entities(entities, update_before_add=True)


class InvalidCapabilityConfigurationError(Exception):
    def __init__(self, key: str, vehicle: Vehicle) -> None:
        super().__init__(
            f"Entity '{key}' has a bad capability configuration for vehicle '{vehicle.info.get_model_name()}'."
        )
