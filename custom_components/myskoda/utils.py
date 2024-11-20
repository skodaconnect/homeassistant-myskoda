import logging

from typing import Callable

from aiohttp.client_exceptions import ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import UpdateFailed

from .coordinator import MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity
from .issues import async_create_spin_issue

_LOGGER = logging.getLogger(__name__)


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
            if not sensor.is_forbidden():
                if sensor.is_supported():
                    entities.append(sensor)

    async_add_entities(entities, update_before_add=True)


def handle_aiohttp_error(
    poll_type: str,
    e: ClientResponseError,
    hass: HomeAssistant,
    config: ConfigEntry,
) -> None:
    _LOGGER.debug("Received error %d with content %s", e.status, e.message)

    if e.status == 412:
        # Handle precondition failed by creating an issue for incorrect S-PIN
        async_create_spin_issue(hass, config.entry_id)
        return

    elif e.status == 500:
        # Log message for error 500, otherwise ignore
        _LOGGER.error(
            f"Error requesting {poll_type} from MySkoda API: {e.message} ({e.status}), ignoring this"
        )
        return
    else:
        raise UpdateFailed(
            f"Error requesting {poll_type} from MySkoda API: {e.message} ({e.status})"
        )
