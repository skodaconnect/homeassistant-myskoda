"""Device Tracker entities for MySkoda."""

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from myskoda.models.info import CapabilityId
from myskoda.models.position import Positions

from .const import COORDINATOR, DOMAIN
from .coordinator import MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity
from .utils import InvalidCapabilityConfigurationError, add_supported_entities


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    add_supported_entities(
        available_entities=[DeviceTracker],
        coordinator=hass.data[DOMAIN][config.entry_id][COORDINATOR],
        async_add_entities=async_add_entities,
    )


class DeviceTracker(MySkodaEntity, TrackerEntity):
    """GPS device tracker for MySkoda."""

    def __init__(self, coordinator: MySkodaDataUpdateCoordinator, vin: str) -> None:  # noqa: D107
        title = coordinator.data.vehicles[vin].info.specification.title
        self.entity_description = EntityDescription(
            name=title,
            key=f"{vin}_device_tracker",
            translation_key="device_tracker",
        )
        super().__init__(coordinator, vin)

    def _positions(self) -> Positions:
        positions = self.vehicle.positions
        if positions is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )
        return positions

    @property
    def source_type(self) -> SourceType:  # noqa: D102
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:  # noqa: D102
        return self._positions().positions[0].gps_coordinates.latitude

    @property
    def longitude(self) -> float | None:  # noqa: D102
        return self._positions().positions[0].gps_coordinates.longitude

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.PARKING_POSITION]
