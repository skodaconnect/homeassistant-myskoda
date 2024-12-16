"""Images for the MySkoda integration."""

import logging

from homeassistant.components.image import (
    ImageEntity,
    ImageEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]

from .const import COORDINATORS, DOMAIN
from .coordinator import MySkodaDataUpdateCoordinator
from .entity import MySkodaEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the image platform."""

    entities = []
    for vin in hass.data[DOMAIN][config.entry_id][COORDINATORS]:
        for SensorClass in [MainRenderImage]:
            entities.append(
                SensorClass(
                    hass.data[DOMAIN][config.entry_id][COORDINATORS][vin], vin, hass
                )
            )

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


class MainRenderImage(MySkodaImage):
    """Main render of the vehicle."""

    entity_description = ImageEntityDescription(
        key="render_vehicle_main",
        translation_key="render_vehicle_main",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    @property
    def image_url(self) -> str | None:
        if render := self.get_renders().get("main"):
            return render
        elif render := self.get_composite_renders().get("unmodified_exterior_front"):
            _LOGGER.debug("Main render not found, choosing composite render instead.")
            render_list = self.get_composite_renders().get("unmodified_exterior_front")
            if isinstance(render_list, list) and render_list:
                for render in render_list:
                    if isinstance(render, dict) and "exterior_front" in render:
                        return render["exterior_front"]

        else:
            _LOGGER.debug("'unmodified_exterior_front' not found, falling back to 'unmodified_exterior_side'.")
            render_list = self.get_composite_renders().get("unmodified_exterior_side")
            if isinstance(render_list, list) and render_list:
                for render in render_list:
                    if isinstance(render, dict) and "exterior_side" in render:
                        return render["exterior_side"]
    
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
