from typing import Callable

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from myskoda.models.common import Vin

from .coordinator import MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity


def add_supported_entities(
    available_entities: list[
        Callable[[MySkodaDataUpdateCoordinator, Vin], MySkodaEntity]
    ],
    coordinators: dict[Vin, MySkodaDataUpdateCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    entities = []

    for vin in coordinators:
        for SensorClass in available_entities:
            sensor = SensorClass(coordinators[vin], vin)
            if not sensor.is_forbidden():
                if sensor.is_supported():
                    entities.append(sensor)

    async_add_entities(entities, update_before_add=True)
