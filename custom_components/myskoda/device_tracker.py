"""Device Tracker entities for MySkoda."""

import logging

from homeassistant.components.device_tracker.config_entry import (
    TrackerEntity,
    TrackerEntityDescription,
)
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]

from myskoda.models.info import CapabilityId
from myskoda.models.position import Error, ErrorType, Position, Positions, PositionType

from .const import COORDINATORS, DOMAIN
from .coordinator import MySkodaConfigEntry, MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity
from .utils import add_supported_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: MySkodaConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    add_supported_entities(
        available_entities=[DeviceTracker],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class DeviceTracker(MySkodaEntity, TrackerEntity):
    """GPS device tracker for MySkoda."""

    def __init__(self, coordinator: MySkodaDataUpdateCoordinator, vin: str) -> None:  # noqa: D107
        title = coordinator.data.vehicle.info.specification.title
        self.entity_description = TrackerEntityDescription(
            name=title,
            key=f"{vin}_device_tracker",
            translation_key="device_tracker",
        )
        super().__init__(coordinator, vin)

    def _positions(self) -> Positions | None:
        return self.vehicle.positions

    def _vehicle_position(self) -> Position | None:
        if pos := self._positions():
            if pos.positions:
                return next(
                    pos for pos in pos.positions if pos.type == PositionType.VEHICLE
                )

    def _pos_error(self) -> Error | None:
        if pos := self._positions():
            if pos.errors:
                return next(
                    err for err in pos.errors if err.type == ErrorType.VEHICLE_IN_MOTION
                )

    @property
    def source_type(self) -> SourceType:  # noqa: D102
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:  # noqa: D102
        position = self._vehicle_position()
        if position is None:
            return None
        return position.gps_coordinates.latitude

    @property
    def longitude(self) -> float | None:  # noqa: D102
        position = self._vehicle_position()
        if position is None:
            return None
        return position.gps_coordinates.longitude

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        attributes = {}

        if render := self.get_renders().get("main"):
            attributes["entity_picture"] = render
        elif render := self.get_composite_renders().get("unmodified_exterior_front"):
            _LOGGER.debug("Main render not found, choosing composite render instead.")
            render_list = self.get_composite_renders().get("unmodified_exterior_front")
            if isinstance(render_list, list) and render_list:
                for render in render_list:
                    if isinstance(render, dict) and "exterior_front" in render:
                        attributes["entity_picture"] = render["exterior_front"]
                        break
        else:
            _LOGGER.debug(
                "'unmodified_exterior_front' not found, falling back to 'unmodified_exterior_side'."
            )
            render_list = self.get_composite_renders().get("unmodified_exterior_side")
            if isinstance(render_list, list) and render_list:
                for render in render_list:
                    if isinstance(render, dict) and "exterior_side" in render:
                        attributes["entity_picture"] = render["exterior_side"]
                        break

        return attributes

    @property
    def location_name(self) -> str | None:
        if err := self._pos_error():
            if err.type == ErrorType.VEHICLE_IN_MOTION:
                return "vehicle_in_motion"

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.PARKING_POSITION]
