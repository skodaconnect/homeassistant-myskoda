"""Images for the MySkoda integration."""

import logging
from datetime import UTC, datetime, timedelta

import httpx
from homeassistant.components.image import (
    GET_IMAGE_TIMEOUT,
    ImageEntity,
    ImageEntityDescription,
)
from homeassistant.const import (
    EntityCategory,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import (
    DiscoveryInfoType,  # pyright: ignore [reportAttributeAccessIssue]
)

from myskoda.models.info import ViewPoint, ViewType

from .const import CACHE_CLOCK_SKEW_TOLERANCE_IN_HOURS
from .coordinator import MySkodaConfigEntry, MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: MySkodaConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the image platform."""

    entities = []
    for vin, coordinator in config.runtime_data.items():
        for SensorClass in [
            MainRenderImage,
            LightStatusImage,
        ]:
            entities.append(SensorClass(coordinator, vin, hass))

    async_add_entities(entities)


class MySkodaImage(MySkodaEntity, ImageEntity):
    """Representation of an Image for MySkoda."""

    vin: str
    coordinator: MySkodaDataUpdateCoordinator
    hass: HomeAssistant

    def __init__(
        self,
        coordinator: MySkodaDataUpdateCoordinator,
        vin: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the Image for MySkoda."""
        ImageEntity.__init__(self, hass)
        super().__init__(coordinator, vin)


class StatusImage(MySkodaImage):
    """A render of the current status of the vehicle."""

    async def _fetch_url(self, url: str) -> httpx.Response | None:
        """Fetch a URL passing in the MySkoda access token."""

        try:
            response = await self._client.get(
                url,
                timeout=GET_IMAGE_TIMEOUT,
                follow_redirects=True,
                headers={
                    "authorization": f"Bearer {await self.coordinator.myskoda.authorization.get_access_token()}"
                },
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            _LOGGER.error("%s: Timeout getting image from %s", self.entity_id, url)
            return None
        except (httpx.RequestError, httpx.HTTPStatusError) as err:
            _LOGGER.error(
                "%s: Error getting new image from %s: %s",
                self.entity_id,
                url,
                err,
            )
            return None
        return response

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if status := self.vehicle.status:
            if ts := status.car_captured_timestamp:
                threshold = datetime.now(UTC) + timedelta(hours=CACHE_CLOCK_SKEW_TOLERANCE_IN_HOURS)
                if ts > threshold:
                    _LOGGER.warning(
                        "Timestamp %s is more than %sh ahead; possible vehicle clock issue.",
                        ts,
                        CACHE_CLOCK_SKEW_TOLERANCE_IN_HOURS,
                    )
                elif ts != self._attr_image_last_updated:
                    _LOGGER.debug("Image updated. Flushing caches.")
                    self._cached_image = None
                    self._attr_image_last_updated = ts
        super()._handle_coordinator_update()


class MainRenderImage(MySkodaImage):
    """Main render of the vehicle."""

    entity_description = ImageEntityDescription(
        key="render_vehicle_main",
        translation_key="render_vehicle_main",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    @property
    def image_url(self) -> str | None:
        if render := self.get_renders().get(ViewPoint.MAIN):
            return render
        elif renders := self.get_composite_renders().get(
            ViewType.UNMODIFIED_EXTERIOR_FRONT
        ):
            _LOGGER.debug("Main render not found, choosing composite render instead.")
            return renders.get(ViewPoint.EXTERIOR_FRONT)
        elif renders := self.get_composite_renders().get(
            ViewType.UNMODIFIED_EXTERIOR_SIDE
        ):
            _LOGGER.debug(
                "'unmodified_exterior_front' not found, falling back to 'unmodified_exterior_side'."
            )
            return renders.get(ViewPoint.EXTERIOR_SIDE)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        attributes = {}
        if render := self.get_renders():
            attributes["vehicle_renders"] = {}
            for r in render:
                attributes["vehicle_renders"][r] = render[r]

        if composite_renders := self.get_composite_renders():
            attributes["composite_renders"] = {}
            for r in composite_renders:
                attributes["composite_renders"][r] = composite_renders[r]
        return attributes


class LightStatusImage(StatusImage):
    """Light 3x render of the vehicle status."""

    entity_description = ImageEntityDescription(
        key="render_light_3x",
        translation_key="render_light_3x",
        entity_registry_enabled_default=False,
    )

    @property
    def image_url(self) -> str | None:
        if status := self.vehicle.status:
            return status.renders.light_mode.three_x
