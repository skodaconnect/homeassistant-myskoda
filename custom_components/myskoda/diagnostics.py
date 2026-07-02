"""Diagnostics support for MySkoda integration."""

import logging
import json
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from myskoda.models.fixtures import Endpoint
from typing import Any


from .coordinator import MySkodaConfigEntry, VehicleCoordinators

_LOGGER = logging.getLogger(__name__)


async def async_get_device_diagnostics(
    hass: HomeAssistant, config_entry: MySkodaConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for selected vehicle."""
    if not (vin := device.serial_number):
        error_message = "No VIN found for this device"
        _LOGGER.error(error_message)
        return {
            "error": error_message,
        }

    vehicle_coords: VehicleCoordinators | None = config_entry.runtime_data.get(vin)

    if not vehicle_coords:
        error_message = f"No coordinator found for VIN: {vin}"
        _LOGGER.error(error_message)
        return {
            "error": error_message,
        }

    coordinator = vehicle_coords.primary
    try:
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
    hass: HomeAssistant, config_entry: MySkodaConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for all vehicles in the config entry."""
    results = []

    for vin, vehicle_coords in config_entry.runtime_data.items():
        coordinator = vehicle_coords.primary
        try:
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

            results.append({"fixtures": json.loads(result.to_json())})

        except Exception as e:
            error_message = f"Error generating diagnostics for VIN {vin}: {e}"
            _LOGGER.error(error_message)
            results.append({"error": error_message})

    return {"results": results}
