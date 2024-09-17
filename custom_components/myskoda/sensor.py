"""Sensors for the MySkoda integration."""

from typing import cast
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from myskoda import Vehicle, charging

from .const import DATA_COODINATOR, DOMAIN
from .entity import MySkodaDataEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config.entry_id][DATA_COODINATOR]

    vehicles = cast(list[Vehicle], coordinator.data.get("vehicles"))

    entities = []

    for vehicle in vehicles:
        entities.append(SoftwareVersion(coordinator, vehicle))
        entities.append(RemainingDistance(coordinator, vehicle))
        entities.append(Mileage(coordinator, vehicle))
        entities.append(LastUpdated(coordinator, vehicle))

        if vehicle.charging and vehicle.charging.status:
            entities.append(TargetBatteryPercentage(coordinator, vehicle))
            entities.append(ChargeType(coordinator, vehicle))
            entities.append(ChargingState(coordinator, vehicle))
            entities.append(RemainingChargingTime(coordinator, vehicle))
            entities.append(BatteryPercentage(coordinator, vehicle))
            entities.append(ChargingPower(coordinator, vehicle))

    async_add_entities(entities, update_before_add=True)


class MySkodaSensor(MySkodaDataEntity, SensorEntity):
    """Base class for all MySkoda sensors."""

    def __init__(  # noqa: D107
        self,
        coordinator: DataUpdateCoordinator,
        vehicle: Vehicle,
        entity_description: EntityDescription,
    ) -> None:
        super().__init__(coordinator, vehicle, entity_description)
        SensorEntity.__init__(self)


class SoftwareVersion(MySkodaSensor):
    """Current software version of a vehicle."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            SensorEntityDescription(
                key="software_version",
                name=f"{vehicle.info.specification.title} Software Version",
                icon="mdi:update",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_software_version"

    @property
    def native_value(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.info.software_version


class BatteryPercentage(MySkodaSensor):
    """Battery charging state in percent."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            SensorEntityDescription(
                key="battery_percentage",
                name=f"{vehicle.info.specification.title} Battery Percentage",
                icon="mdi:battery",
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=PERCENTAGE,
                device_class=SensorDeviceClass.BATTERY,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_battery_percentage"

    @property
    def native_value(self):  # noqa: D102
        if not self.coordinator.data or not self.vehicle.charging.status:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.status.battery.state_of_charge_in_percent

    @property
    def icon(self):  # noqa: D102
        if not self.coordinator.data or not self.vehicle.charging.status:
            return "mdi:battery-unknown"

        self._update_device_from_coordinator()

        suffix = ""

        if self.vehicle.charging.status.battery.state_of_charge_in_percent >= 95:
            suffix = "100"
        elif self.vehicle.charging.status.battery.state_of_charge_in_percent >= 85:
            suffix = "90"
        elif self.vehicle.charging.status.battery.state_of_charge_in_percent >= 75:
            suffix = "80"
        elif self.vehicle.charging.status.battery.state_of_charge_in_percent >= 65:
            suffix = "70"
        elif self.vehicle.charging.status.battery.state_of_charge_in_percent >= 55:
            suffix = "60"
        elif self.vehicle.charging.status.battery.state_of_charge_in_percent >= 45:
            suffix = "50"
        elif self.vehicle.charging.status.battery.state_of_charge_in_percent >= 35:
            suffix = "40"
        elif self.vehicle.charging.status.battery.state_of_charge_in_percent >= 25:
            suffix = "30"
        elif self.vehicle.charging.status.battery.state_of_charge_in_percent >= 15:
            suffix = "20"
        elif self.vehicle.charging.status.battery.state_of_charge_in_percent >= 5:
            suffix = "10"
        else:
            suffix = "outline"

        if self.vehicle.charging.status.state != charging.ChargingState.CONNECT_CABLE:
            return f"mdi:battery-charging-{suffix}"
        if suffix == "100":
            return "mdi:battery"
        return f"mdi:battery-{suffix}"


class ChargingPower(MySkodaSensor):
    """How fast the car is charging in kW."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            SensorEntityDescription(
                key="charging_power",
                name=f"{vehicle.info.specification.title} Charging Power",
                icon="mdi:lightning-bolt",
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfPower.KILO_WATT,
                device_class=SensorDeviceClass.POWER,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_charging_power"

    @property
    def native_value(self):  # noqa: D102
        if not self.coordinator.data or not self.vehicle.charging.status:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.status.charge_power_in_kw


class RemainingDistance(MySkodaSensor):
    """Estimated range of an electric vehicle in km."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            SensorEntityDescription(
                key="range",
                name=f"{vehicle.info.specification.title} Range",
                icon="mdi:speedometer",
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfLength.KILOMETERS,
                device_class=SensorDeviceClass.DISTANCE,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_range"

    @property
    def native_value(self):  # noqa: D102
        if not self.coordinator.data or not self.vehicle.charging.status:
            return None

        self._update_device_from_coordinator()

        return (
            self.vehicle.charging.status.battery.remaining_cruising_range_in_meters
            / 1000
        )


class TargetBatteryPercentage(MySkodaSensor):
    """Charging target of the EV's battery in percent."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            SensorEntityDescription(
                key="target_battery_percentage",
                name=f"{vehicle.info.specification.title} Target Battery Percentage",
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=PERCENTAGE,
                icon="mdi:percent",
                device_class=SensorDeviceClass.BATTERY,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_target_battery_percentage"

    @property
    def native_value(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.settings.target_state_of_charge_in_percent


class Mileage(MySkodaSensor):
    """The vehicle's mileage (total kilometers driven)."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            SensorEntityDescription(
                key="milage",
                name=f"{vehicle.info.specification.title} Milage",
                state_class=SensorStateClass.TOTAL_INCREASING,
                native_unit_of_measurement=UnitOfLength.KILOMETERS,
                icon="mdi:counter",
                device_class=SensorDeviceClass.DISTANCE,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_milage"

    @property
    def native_value(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.health.mileage_in_km


class ChargeType(MySkodaSensor):
    """How the vehicle is being charged (AC/DC)."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            SensorEntityDescription(
                key="charge_type",
                name=f"{vehicle.info.specification.title} Charge Type",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_charge_type"

    @property
    def native_value(self):  # noqa: D102
        if not self.coordinator.data or not self.vehicle.charging.status:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.status.charge_type

    @property
    def icon(self):  # noqa: D102
        if not self.coordinator.data or not self.vehicle.charging.status:
            return "mdi:ev-plug-type2"

        self._update_device_from_coordinator()

        if self.vehicle.charging.status.charge_type == "AC":
            return "mdi:ev-plug-type2"
        return "mdi:ev-plug-ccs2"


class ChargingState(MySkodaSensor):
    """Current state of charging (ready, charging, conserving, ...)."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            SensorEntityDescription(
                key="charging_state",
                name=f"{vehicle.info.specification.title} Charging State",
                device_class=SensorDeviceClass.ENUM,
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_charging_state"
        self._attr_options = [
            "CONNECT_CABLE",
            "READY_FOR_CHARGING",
            "CONSERVING",
            "CHARGING",
        ]

    @property
    def native_value(self):  # noqa: D102
        if not self.coordinator.data or not self.vehicle.charging.status:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.status.state

    @property
    def icon(self):  # noqa: D102
        if not self.coordinator.data or not self.vehicle.charging.status:
            return "mdi:power_plug"

        self._update_device_from_coordinator()

        if self.vehicle.charging.status.state == charging.ChargingState.CONNECT_CABLE:
            return "mdi:power-plug-off"
        return "mdi:power-plug"


class RemainingChargingTime(MySkodaSensor):
    """Estimation on when the vehicle will be fully charged."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            SensorEntityDescription(
                key="remaining_charging_time",
                name=f"{vehicle.info.specification.title} Remaining Charging Time",
                device_class=SensorDeviceClass.DURATION,
                native_unit_of_measurement=UnitOfTime.MINUTES,
                icon="mdi:timer",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_remaining_charging_time"

    @property
    def native_value(self):  # noqa: D102
        if not self.coordinator.data or not self.vehicle.charging.status:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.charging.status.remaining_time_to_fully_charged_in_minutes


class LastUpdated(MySkodaSensor):
    """Timestamp of when the car has sent the last update to the MySkoda server."""

    def __init__(self, coordinator: DataUpdateCoordinator, vehicle: Vehicle) -> None:  # noqa: D107
        super().__init__(
            coordinator,
            vehicle,
            SensorEntityDescription(
                key="car_captured",
                name=f"{vehicle.info.specification.title} Last Updated",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:clock",
            ),
        )
        self._attr_unique_id = f"{vehicle.info.vin}_car_captured"

    @property
    def native_value(self):  # noqa: D102
        if not self.coordinator.data:
            return None

        self._update_device_from_coordinator()

        return self.vehicle.status.car_captured_timestamp
