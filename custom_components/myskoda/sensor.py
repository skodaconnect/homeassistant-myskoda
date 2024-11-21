"""Sensors for the MySkoda integration."""

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType  # pyright: ignore [reportAttributeAccessIssue]

from myskoda.models import charging
from myskoda.models.charging import Charging, ChargingStatus
from myskoda.models.info import CapabilityId
from myskoda.models.driving_range import EngineType

from .const import COORDINATORS, DOMAIN
from .entity import MySkodaEntity
from .utils import add_supported_entities


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    _discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    add_supported_entities(
        available_entities=[
            BatteryPercentage,
            ChargeType,
            ChargingPower,
            ChargingRate,
            ChargingState,
            LastUpdated,
            Mileage,
            RemainingChargingTime,
            Range,
            SoftwareVersion,
            TargetBatteryPercentage,
            InspectionInterval,
            ElectricRange,
            CombustionRange,
            FuelLevel,
            InspectionIntervalKM,
            OilServiceIntervalDays,
            OilServiceIntervalKM,
        ],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaSensor(MySkodaEntity, SensorEntity):
    pass


class SoftwareVersion(MySkodaSensor):
    """Current software version of a vehicle."""

    entity_description = SensorEntityDescription(
        key="software_version",
        translation_key="software_version",
    )

    @property
    def native_value(self):  # noqa: D102
        return self.vehicle.info.software_version

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING_MEB]


class ChargingSensor(MySkodaSensor):
    def _charging(self) -> Charging | None:
        if charging := self.vehicle.charging:
            return charging

    def _status(self) -> ChargingStatus | None:
        if charging := self._charging():
            if status := charging.status:
                return status

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING]


class BatteryPercentage(ChargingSensor):
    """Battery charging state in percent."""

    entity_description = SensorEntityDescription(
        key="battery_percentage",
        icon="mdi:battery",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        translation_key="battery_percentage",
    )

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if status := self._status():
            return status.battery.state_of_charge_in_percent

    @property
    def icon(self) -> str:  # noqa: D102
        if not (status := self._status()):
            return "mdi:battery-outline"

        if status.battery.state_of_charge_in_percent >= 95:
            suffix = "100"
        elif status.battery.state_of_charge_in_percent >= 85:
            suffix = "90"
        elif status.battery.state_of_charge_in_percent >= 75:
            suffix = "80"
        elif status.battery.state_of_charge_in_percent >= 65:
            suffix = "70"
        elif status.battery.state_of_charge_in_percent >= 55:
            suffix = "60"
        elif status.battery.state_of_charge_in_percent >= 45:
            suffix = "50"
        elif status.battery.state_of_charge_in_percent >= 35:
            suffix = "40"
        elif status.battery.state_of_charge_in_percent >= 25:
            suffix = "30"
        elif status.battery.state_of_charge_in_percent >= 15:
            suffix = "20"
        elif status.battery.state_of_charge_in_percent >= 5:
            suffix = "10"
        else:
            suffix = "outline"

        if status.state != charging.ChargingState.CONNECT_CABLE:
            return f"mdi:battery-charging-{suffix}"
        if suffix == "100":
            return "mdi:battery"
        return f"mdi:battery-{suffix}"


class ChargingPower(ChargingSensor):
    """How fast the car is charging in kW."""

    entity_description = SensorEntityDescription(
        key="charging_power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        translation_key="charging_power",
    )

    @property
    def native_value(self) -> float | None:  # noqa: D102
        if status := self._status():
            return status.charge_power_in_kw

    def forbidden_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING_MQB]


class CombustionRange(MySkodaSensor):
    """The vehicle's combustion range - only for hybrid vehicles."""

    entity_description = SensorEntityDescription(
        key="combustion_range",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        translation_key="combustion_range",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if range := self.vehicle.driving_range:
            if range.primary_engine_range is not None:
                return range.primary_engine_range.remaining_range_in_km

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE, CapabilityId.FUEL_STATUS, CapabilityId.CHARGING_MQB]


class ElectricRange(MySkodaSensor):
    """The vehicle's electric range - only for hybrid vehicles."""

    entity_description = SensorEntityDescription(
        key="electric_range",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        translation_key="electric_range",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if range := self.vehicle.driving_range:
            if range.secondary_engine_range is not None:
                return range.secondary_engine_range.remaining_range_in_km

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE, CapabilityId.FUEL_STATUS, CapabilityId.CHARGING_MQB]


class FuelLevel(MySkodaSensor):
    """The vehicle's combustion engine fuel level - only for non electric vehicles."""

    entity_description = SensorEntityDescription(
        key="fuel_level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        translation_key="fuel_level",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if range := self.vehicle.driving_range:
            return range.primary_engine_range.current_fuel_level_in_percent

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE, CapabilityId.FUEL_STATUS]


class Range(MySkodaSensor):
    """Estimated range of vehicle in km."""

    entity_description = SensorEntityDescription(
        key="range",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        translation_key="range",
    )

    @property
    def icon(self) -> str:  # noqa: D102
        if (
            self.vehicle.driving_range is None
            or self.vehicle.driving_range.car_type is None
        ):
            return "mdi:gas-station"
        else:
            if self.vehicle.driving_range.car_type == EngineType.ELECTRIC:
                return "mdi:ev-station"
            else:
                return "mdi:gas-station"

    @property
    def native_value(self) -> int | float | None:  # noqa: D102
        if range := self.vehicle.driving_range:
            return range.total_range_in_km

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE]


class TargetBatteryPercentage(ChargingSensor):
    """Charging target of the EV's battery in percent."""

    entity_description = SensorEntityDescription(
        key="target_battery_percentage",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        translation_key="target_battery_percentage",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if charging := self._charging():
            return charging.settings.target_state_of_charge_in_percent

    def forbidden_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING_MQB]


class Mileage(MySkodaSensor):
    """The vehicle's mileage (total kilometers driven)."""

    entity_description = SensorEntityDescription(
        key="milage",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        translation_key="mileage",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if health := self.vehicle.health:
            return health.mileage_in_km

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.VEHICLE_HEALTH_INSPECTION]


class InspectionInterval(MySkodaSensor):
    """The number of days before next inspection."""

    entity_description = SensorEntityDescription(
        key="inspection",
        # Not a duration until https://github.com/home-assistant/frontend/issues/18151 is fixed
        # device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.DAYS,
        translation_key="inspection",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if maintenance_report := self.vehicle.maintenance.maintenance_report:
            return maintenance_report.inspection_due_in_days

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.VEHICLE_HEALTH_INSPECTION]


class InspectionIntervalKM(MySkodaSensor):
    """The number of kilometers before inspection is due."""

    entity_description = SensorEntityDescription(
        key="inspection_in_km",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        translation_key="inspection_in_km",
    )

    @property
    def native_value(self) -> int | None:  # noqa: S102
        if maintenance_report := self.vehicle.maintenance.maintenance_report:
            return maintenance_report.inspection_due_in_km

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.VEHICLE_HEALTH_INSPECTION, CapabilityId.FUEL_STATUS]


class OilServiceIntervalDays(MySkodaSensor):
    """The number of days before oil service is due."""

    entity_description = SensorEntityDescription(
        key="oil_service_in_days",
        # Not a duration until https://github.com/home-assistant/frontend/issues/18151 is fixed
        # device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.DAYS,
        translation_key="oil_service_in_days",
    )

    @property
    def native_value(self) -> int | None:  # noqa: S102
        if maintenance_report := self.vehicle.maintenance.maintenance_report:
            return maintenance_report.oil_service_due_in_days

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.VEHICLE_HEALTH_INSPECTION, CapabilityId.FUEL_STATUS]


class OilServiceIntervalKM(MySkodaSensor):
    """The number of kilometers before oil service is due."""

    entity_description = SensorEntityDescription(
        key="oil_service_in_km",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        translation_key="oil_service_in_km",
    )

    @property
    def native_value(self) -> int | None:  # noqa: S102
        if maintenance_report := self.vehicle.maintenance.maintenance_report:
            return maintenance_report.oil_service_due_in_km

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.VEHICLE_HEALTH_INSPECTION, CapabilityId.FUEL_STATUS]


class ChargeType(ChargingSensor):
    """How the vehicle is being charged (AC/DC)."""

    entity_description = SensorEntityDescription(
        key="charge_type",
        translation_key="charge_type",
    )

    @property
    def native_value(self) -> str | None:  # noqa: D102
        if status := self._status():
            if status.charge_type:
                return str(status.charge_type).lower()


class ChargingState(ChargingSensor):
    """Current state of charging (ready, charging, conserving, ...)."""

    entity_description = SensorEntityDescription(
        key="charging_state",
        device_class=SensorDeviceClass.ENUM,
        translation_key="charging_state",
    )

    # lower_snake_case for translations
    _attr_options = [
        "connect_cable",
        "ready_for_charging",
        "conserving",
        "charging",
    ]

    @property
    def native_value(self) -> str | None:  # noqa: D102
        if status := self._status():
            if status.state:
                return str(status.state).lower()


class RemainingChargingTime(ChargingSensor):
    """Estimation on when the vehicle will be fully charged."""

    entity_description = SensorEntityDescription(
        key="remaining_charging_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        translation_key="remaining_charging_time",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if status := self._status():
            return status.remaining_time_to_fully_charged_in_minutes


class ChargingRate(ChargingSensor):
    """Estimation on how many kmh are being charged."""

    entity_description = SensorEntityDescription(
        key="charging_rate",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        translation_key="charging_rate",
    )

    @property
    def native_value(self) -> float | None:
        if status := self._status():
            return status.charging_rate_in_kilometers_per_hour

    def forbidden_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING_MQB]


class LastUpdated(MySkodaSensor):
    """Timestamp of when the car has sent the last update to the MySkoda server."""

    entity_description = SensorEntityDescription(
        key="car_captured",
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key="car_captured",
    )

    @property
    def native_value(self) -> datetime | None:  # noqa: D102
        if status := self.vehicle.status:
            return status.car_captured_timestamp

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE]
