"""Oilfox metering."""

from pickle import TRUE

from .enyaq import EnyaqHub, Vehicle
from .const import DATA_COODINATOR, DOMAIN
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""\
    
    coordinator = hass.data[DOMAIN][config.entry_id][DATA_COODINATOR]

    vehicles = coordinator.data

    entities = []

    for vehicle in vehicles:
        entities.append(EnyaqSensorSoftwareVersion(coordinator, vehicle))
        entities.append(EnyaqSensorBatteryPercentage(coordinator, vehicle))
        entities.append(EnyaqSensorChargingPower(coordinator, vehicle))
        entities.append(EnyaqSensorRemainingDistance(coordinator, vehicle))
        entities.append(EnyaqSensorTargetBatteryPercentage(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class EnyaqSensor(CoordinatorEntity, SensorEntity):
    hub: EnyaqHub
    vehicle: Vehicle

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(coordinator)

        self.vehicle = vehicle

    @property
    def device_info(self) -> DeviceInfo:
        return {
            "identifiers": {(DOMAIN, self.vehicle.info.vin)},
            "name": self.vehicle.info.title,
            "manufacturer": "Škoda",
            "sw_version": self.vehicle.info.software_version,
            "hw_version": f"{self.vehicle.info.model_id}-{self.vehicle.info.model_year}",
            "model": self.vehicle.info.model,
        }

    def _update_device_from_coordinator(self) -> None:
        for vehicle in self.coordinator.data:
            if vehicle.info.vin == self.vehicle.info.vin:
                self.vehicle = vehicle
                return

class EnyaqSensorSoftwareVersion(EnyaqSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(coordinator, vehicle)

        self._attr_name = f"{self.vehicle.info.title} Software Version"
        self._attr_unique_id = f"{self.vehicle.info.vin}_software_version"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:update"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.vehicle.info.software_version

class EnyaqSensorBatteryPercentage(EnyaqSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(coordinator, vehicle)

        self._attr_name = f"{self.vehicle.info.title} Battery Percentage"
        self._attr_unique_id = f"{self.vehicle.info.vin}_battery_percentage"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:battery"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.vehicle.charging.battery_percent

    @property
    def icon(self):
        if not self.coordinator.data:
            return "mdi:battery-unknown"
        
        self._update_device_from_coordinator()

        suffix = ""

        if self.vehicle.charging.battery_percent >= 95:
            suffix = "100"
        elif self.vehicle.charging.battery_percent >= 85:
            suffix = "90"
        elif self.vehicle.charging.battery_percent >= 75:
            suffix = "80"
        elif self.vehicle.charging.battery_percent >= 65:
            suffix = "70"
        elif self.vehicle.charging.battery_percent >= 55:
            suffix = "60"
        elif self.vehicle.charging.battery_percent >= 45:
            suffix = "50"
        elif self.vehicle.charging.battery_percent >= 35:
            suffix = "40"
        elif self.vehicle.charging.battery_percent >= 25:
            suffix = "30"
        elif self.vehicle.charging.battery_percent >= 15:
            suffix = "20"
        elif self.vehicle.charging.battery_percent >= 5:
            suffix = "10"
        else:
            suffix = "outline"

        if self.vehicle.charging.state != "CONNECT_CABLE":
            return f"mdi:battery-charging-{suffix}"
        else:
            if suffix == "100":
                return "mdi:battery"
            return f"mdi:battery-{suffix}"

class EnyaqSensorChargingPower(EnyaqSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(coordinator, vehicle)

        self._attr_name = f"{self.vehicle.info.title} Charging Power"
        self._attr_unique_id = f"{self.vehicle.info.vin}_charging_power"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.vehicle.charging.charging_power_kw

class EnyaqSensorRemainingDistance(EnyaqSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(coordinator, vehicle)

        self._attr_name = f"{self.vehicle.info.title} Range"
        self._attr_unique_id = f"{self.vehicle.info.vin}_range"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.vehicle.charging.remaining_distance_m / 1000

class EnyaqSensorTargetBatteryPercentage(EnyaqSensor):
    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:
        super().__init__(coordinator, vehicle)

        self._attr_name = f"{self.vehicle.info.title} Target Battery Percentage"
        self._attr_unique_id = f"{self.vehicle.info.vin}_target_battery_percentage"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:percent"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        
        self._update_device_from_coordinator()

        return self.vehicle.charging.target_percent