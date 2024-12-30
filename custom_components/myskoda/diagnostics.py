"""Diagnostics support for MySkoda integration."""

import logging
import json
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntry
from myskoda.models.fixtures import Endpoint
from typing import Any


from .const import DOMAIN, COORDINATORS
from .coordinator import MySkodaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for selected vehicle."""
    if not (vin := device.serial_number):
        error_message = "No VIN found for this device"
        _LOGGER.error(error_message)
        return {
            "error": error_message,
        }

    coordinator: MySkodaDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ][COORDINATORS][vin]

    if not coordinator:
        error_message = f"No coordinator found for VIN: {vin}"
        _LOGGER.error(error_message)
        return {
            "error": error_message,
        }

    try:
        # Fetch diagnostics data from the MySkoda API
        specs = coordinator.data.vehicle.info.specification
        description = (
            f"Fixtures for {specs.model} {specs.trim_level} {specs.model_year}"
        )

        result = await coordinator.myskoda.generate_get_fixture(
            coordinator.data.vehicle.info.specification.model,
            description,
            [vin],
            Endpoint.ALL,
        )

        return {
            "fixtures": json.loads(result.to_json()),
        }

    except Exception as e:
        error_message = f"Error generating fixtures for VIN {vin}: {e}"
        _LOGGER.error(error_message)
        return {
            "error": error_message,
        }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for all vehicles in the config entry."""
    coordinators = hass.data[DOMAIN][config_entry.entry_id][COORDINATORS]
    results = []

    for vin, coordinator in coordinators.items():
        if not coordinator:
            error_message = f"No coordinator found for VIN: {vin}"
            _LOGGER.error(error_message)
            results.append({"error": error_message})
            continue

        try:
            # Fetch diagnostics data from the MySkoda API
            specs = coordinator.data.vehicle.info.specification
            description = (
                f"Fixtures for {specs.model} {specs.trim_level} {specs.model_year}"
            )

            result = await coordinator.myskoda.generate_get_fixture(
                coordinator.data.vehicle.info.specification.model,
                description,
                [vin],
                Endpoint.ALL,
            )

            # Append the successful data
            results.append({"fixtures": json.loads(result.to_json())})

        except Exception as e:
            error_message = f"Error generating diagnostics for VIN {vin}: {e}"
            _LOGGER.error(error_message)
            results.append({"error": error_message})

    return {"results": results}
