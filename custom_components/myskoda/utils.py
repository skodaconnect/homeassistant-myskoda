from collections.abc import Sequence
from typing import Callable, Protocol

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from myskoda.models.chargingprofiles import ChargingProfile
from myskoda.models.common import Vin

from .coordinator import MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity


class _HasId(Protocol):
    id: int


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


def add_supported_charging_profile_entities(
    available_entities: list[
        Callable[[MySkodaDataUpdateCoordinator, Vin, int], MySkodaEntity]
    ],
    coordinators: dict[Vin, MySkodaDataUpdateCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register one set of entities per configured charging profile (location).

    Charging profiles can be added by the user at any time (e.g. a new
    charging location saved in the MySkoda app), so this keeps watching each
    coordinator for profile IDs it hasn't seen yet and adds their entities
    without requiring a restart.
    """
    known_profile_ids: dict[Vin, set[int]] = {vin: set() for vin in coordinators}

    def _add_new_profiles(vin: Vin, coordinator: MySkodaDataUpdateCoordinator) -> None:
        profiles = coordinator.data.vehicle.charging_profiles
        if not profiles:
            return

        new_entities = []
        for profile in profiles.charging_profiles:
            if profile.id in known_profile_ids[vin]:
                continue
            known_profile_ids[vin].add(profile.id)

            for EntityClass in available_entities:
                entity = EntityClass(coordinator, vin, profile.id)
                if not entity.is_forbidden() and entity.is_supported():
                    new_entities.append(entity)

        if new_entities:
            async_add_entities(new_entities, update_before_add=True)

    for vin, coordinator in coordinators.items():
        _add_new_profiles(vin, coordinator)
        coordinator.async_add_listener(
            lambda vin=vin, coordinator=coordinator: _add_new_profiles(vin, coordinator)
        )


def add_supported_charging_time_entities(
    available_entities: list[
        Callable[[MySkodaDataUpdateCoordinator, Vin, int, int], MySkodaEntity]
    ],
    entry_selector: Callable[[ChargingProfile], Sequence[_HasId]],
    coordinators: dict[Vin, MySkodaDataUpdateCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register one set of entities per entry nested within a charging profile.

    Entries (e.g. preferred charging times or charging timers, selected via
    `entry_selector`) can be added by the user at any time (e.g. a new time
    window saved in the MySkoda app), so this keeps watching each coordinator
    for (profile_id, entry_id) pairs it hasn't seen yet and adds their
    entities without requiring a restart.
    """
    known_entry_ids: dict[Vin, set[tuple[int, int]]] = {
        vin: set() for vin in coordinators
    }

    def _add_new_entries(vin: Vin, coordinator: MySkodaDataUpdateCoordinator) -> None:
        profiles = coordinator.data.vehicle.charging_profiles
        if not profiles:
            return

        new_entities = []
        for profile in profiles.charging_profiles:
            for entry in entry_selector(profile):
                key = (profile.id, entry.id)
                if key in known_entry_ids[vin]:
                    continue
                known_entry_ids[vin].add(key)

                for EntityClass in available_entities:
                    entity = EntityClass(coordinator, vin, profile.id, entry.id)
                    if not entity.is_forbidden() and entity.is_supported():
                        new_entities.append(entity)

        if new_entities:
            async_add_entities(new_entities, update_before_add=True)

    for vin, coordinator in coordinators.items():
        _add_new_entries(vin, coordinator)
        coordinator.async_add_listener(
            lambda vin=vin, coordinator=coordinator: _add_new_entries(vin, coordinator)
        )
