"""MySkoda Entity base classes."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from myskoda import Vehicle
from myskoda.models.chargingprofiles import ChargingProfile
from myskoda.models.event import OperationEvent
from myskoda.models.info import CapabilityId, ViewPoint, ViewType

from .const import DOMAIN
from .coordinator import (
    MySkodaDataUpdateCoordinator,
    ServiceEvents,
)


class MySkodaEntity(CoordinatorEntity):
    """Base class for all entities in the MySkoda integration."""

    vin: str
    coordinator: MySkodaDataUpdateCoordinator
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
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
    def operations(self) -> dict[str, OperationEvent]:
        return self.coordinator.data.operations

    @property
    def service_events(self) -> ServiceEvents:
        return self.coordinator.data.service_events

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

    def forbidden_capabilities(self) -> list[CapabilityId]:
        return []

    def is_supported(self) -> bool:
        return all(
            self.vehicle.has_capability(cap) for cap in self.required_capabilities()
        )

    def is_forbidden(self) -> bool:
        return any(
            self.vehicle.has_capability(cap) for cap in self.forbidden_capabilities()
        )

    def has_any_capability(self, cap: list[CapabilityId]) -> bool:
        """Check if any capabilities in the list is supported."""
        return any(self.vehicle.has_capability(capability) for capability in cap)

    def has_all_capabilities(self, cap: list[CapabilityId]) -> bool:
        """Check if all capabilities in the list are supported."""
        return all(self.vehicle.has_capability(capability) for capability in cap)

    def get_renders(self) -> dict[ViewPoint, str]:
        """Return a dict of all vehicle image render URLs, keyed by view_point.

        E.g.
        {"main": "https://ip-modcwp.azureedge.net/path/render.png"}
        """
        return {render.view_point: render.url for render in self.vehicle.info.renders}

    def get_composite_renders(self) -> dict[ViewType, dict[ViewPoint, str]]:
        """Return a dict of all vehicle composite render URLs, keyed by view_type.
        Value contains a dict of available renders, keyed by view_point.

        E.g.
        {"home": {"exterior_side": "https://ip-modcwp.azureedge.net/path/render.png"}}
        """
        composite_renders = {}
        for cr in self.vehicle.info.composite_renders:
            composite_renders[cr.view_type] = {
                render.view_point: render.url for render in cr.layers
            }
        return composite_renders


class MySkodaChargingProfileEntity(MySkodaEntity):
    """Base class for entities representing a single charging profile (location).

    Each configured charging location is exposed as its own device, linked to
    the vehicle device via `via_device`.
    """

    profile_id: int

    def __init__(
        self,
        coordinator,
        vin: str,
        profile_id: int,
    ) -> None:  # noqa: D107
        self.profile_id = profile_id
        super().__init__(coordinator, vin)
        self._attr_unique_id = (
            f"{vin}_charging_profile_{profile_id}_{self.entity_description.key}"
        )

    @property
    def charging_profile(self) -> ChargingProfile | None:
        """Return the charging profile this entity represents, if it still exists."""
        profiles = self.coordinator.data.charging_profiles
        if not profiles:
            return None
        for profile in profiles.charging_profiles:
            if profile.id == self.profile_id:
                return profile
        return None

    @property
    def available(self) -> bool:  # noqa: D102
        return super().available and self.charging_profile is not None

    @property
    def device_info(self) -> DeviceInfo:  # noqa: D102
        name = self.charging_profile.name if self.charging_profile else None
        return {
            "identifiers": {(DOMAIN, f"{self.vin}_charging_profile_{self.profile_id}")},
            "name": name or f"Charging Profile {self.profile_id}",
            "via_device": (DOMAIN, self.vehicle.info.vin),
        }

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING_PROFILES]
