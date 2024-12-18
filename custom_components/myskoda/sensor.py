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
    EntityCategory,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import (
    DiscoveryInfoType,  # pyright: ignore [reportAttributeAccessIssue]
)

from myskoda.models import charging
from myskoda.models.charging import Charging, ChargingStatus
from myskoda.models.driving_range import EngineType
from myskoda.models.info import CapabilityId
from myskoda.models.operation_request import OperationStatus

from .const import COORDINATORS, DOMAIN, OUTSIDE_TEMP_MIN_BOUND, OUTSIDE_TEMP_MAX_BOUND
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
            AddBlueRange,
            BatteryPercentage,
            ChargeType,
            ChargingPower,
            ChargingRate,
            ChargingState,
            CombustionRange,
            ElectricRange,
            FuelLevel,
            InspectionInterval,
            InspectionIntervalKM,
            LastUpdated,
            Mileage,
            OilServiceIntervalDays,
            OilServiceIntervalKM,
            Operation,
            OutsideTemperature,
            Range,
            RemainingChargingTime,
            SoftwareVersion,
            TargetBatteryPercentage,
        ],
        coordinators=hass.data[DOMAIN][config.entry_id][COORDINATORS],
        async_add_entities=async_add_entities,
    )


class MySkodaSensor(MySkodaEntity, SensorEntity):
    def _charging(self) -> Charging | None:
        if charging := self.vehicle.charging:
            return charging

    def _status(self) -> ChargingStatus | None:
        if charging := self._charging():
            if status := charging.status:
                return status


class Operation(MySkodaSensor):
    """Report the most recent operation."""

    entity_description = SensorEntityDescription(
        key="operation",
        translation_key="operation",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    _attr_options = [status.value.lower() for status in OperationStatus]

    @property
    def native_value(self) -> str | None:  # noqa: D102
        """Returns the status of the last seen operation."""
        if self.operations:
            last_operation = list(self.operations.values())[-1]
            return last_operation.operation.status.lower()

    @property
    def extra_state_attributes(self) -> dict:
        """Returns additional attributes for the operation sensor.

        - request_id, operation name, error_code and timestamp of the last seen operation.
        - history: a list of dicts with the same fields for the previously seen operations.
        """
        attributes = {}
        if not self.operations:
            return attributes

        operations = list(self.operations.values())
        operations.reverse()
        filtered = [
            {
                "request_id": event.operation.request_id,
                "operation": event.operation.operation,
                "status": event.operation.status.lower(),
                "error_code": event.operation.error_code,
                "timestamp": event.timestamp,
            }
            for event in operations
        ]
        attributes = filtered[0]
        attributes["history"] = filtered[1:]

        return attributes


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
            if status.battery.state_of_charge_in_percent:
                return status.battery.state_of_charge_in_percent

    @property
    def icon(self) -> str:  # noqa: D102
        if not (status := self._status()):
            return "mdi:battery-outline"

        if soc := status.battery.state_of_charge_in_percent:
            if soc >= 95:
                suffix = "100"
            elif soc >= 85:
                suffix = "90"
            elif soc >= 75:
                suffix = "80"
            elif soc >= 65:
                suffix = "70"
            elif soc >= 55:
                suffix = "60"
            elif soc >= 45:
                suffix = "50"
            elif soc >= 35:
                suffix = "40"
            elif soc >= 25:
                suffix = "30"
            elif soc >= 15:
                suffix = "20"
            elif soc >= 5:
                suffix = "10"
            else:
                suffix = "outline"

            if status.state != charging.ChargingState.CONNECT_CABLE:
                return f"mdi:battery-charging-{suffix}"
            if suffix == "100":
                return "mdi:battery"
            return f"mdi:battery-{suffix}"
        return "mdi:battery-unknown"


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


class AddBlueRange(MySkodaSensor):
    """The vehicles's AdBlue range - only for vehicles where its available."""

    entity_description = SensorEntityDescription(
        key="adblue_range",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        translation_key="adblue_range",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if range := self.vehicle.driving_range:
            if range.ad_blue_range is not None:
                return range.ad_blue_range

    def is_supported(self) -> bool:
        if range := self.vehicle.driving_range:
            return range.ad_blue_range is not None
        return False


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
            if primary := range.primary_engine_range:
                if primary.engine_type in [EngineType.GASOLINE, EngineType.DIESEL]:
                    return primary.remaining_range_in_km
            if secondary := range.secondary_engine_range:
                if secondary.engine_type in [EngineType.GASOLINE, EngineType.DIESEL]:
                    return secondary.remaining_range_in_km

    def is_supported(self) -> bool:
        if self.has_all_capabilities([CapabilityId.STATE, CapabilityId.FUEL_STATUS]):
            if range := self.vehicle.driving_range:
                return range.car_type == EngineType.HYBRID
        return False


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


class GasRange(MySkodaSensor):
    """The vehicle's gas range - only for hybrid CNG vehicles."""

    entity_description = SensorEntityDescription(
        key="gas_range",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        translation_key="gas_range",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if range := self.vehicle.driving_range:
            if range.primary_engine_range is not None:
                return range.primary_engine_range.remaining_range_in_km

    def is_supported(self) -> bool:
        if self.has_all_capabilities([CapabilityId.STATE, CapabilityId.FUEL_STATUS]):
            if range := self.vehicle.driving_range:
                return (
                    range.car_type == EngineType.HYBRID
                    and (primary_engine_range := range.primary_engine_range)
                    and primary_engine_range.engine_type == EngineType.CNG
                )
        return False


class GasLevel(MySkodaSensor):
    """The vehicle's gas level - only for hybrid CNG vehicles."""

    entity_description = SensorEntityDescription(
        key="gas_level",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        translation_key="gas_level",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if range := self.vehicle.driving_range:
            return range.primary_engine_range.current_fuel_level_in_percent

    def is_supported(self) -> bool:
        if self.has_all_capabilities([CapabilityId.STATE, CapabilityId.FUEL_STATUS]):
            if range := self.vehicle.driving_range:
                return (
                    range.car_type == EngineType.HYBRID
                    and (primary_engine_range := range.primary_engine_range)
                    and primary_engine_range.engine_type == EngineType.CNG
                )
        return False


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
            if primary := range.primary_engine_range:
                if primary.engine_type in [EngineType.GASOLINE, EngineType.DIESEL]:
                    return primary.current_fuel_level_in_percent
            if secondary := range.secondary_engine_range:
                if secondary.engine_type in [EngineType.GASOLINE, EngineType.DIESEL]:
                    return secondary.current_fuel_level_in_percent

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

    def is_supported(self) -> bool:
        status = self._status()
        driving_range = self.vehicle.driving_range
        return any(
            [
                driving_range and driving_range.total_range_in_km,
                status and status.battery.remaining_cruising_range_in_meters,
            ]
        )

    @property
    def icon(self) -> str:  # noqa: D102
        if (
            self.vehicle.driving_range is None
            or self.vehicle.driving_range.car_type is None
        ):
            return "mdi:ev-station"
        else:
            if self.vehicle.driving_range.car_type == EngineType.ELECTRIC:
                return "mdi:ev-station"
            else:
                return "mdi:gas-station"

    @property
    def native_value(self) -> int | float | None:  # noqa: D102
        if range := self.vehicle.driving_range:
            return range.total_range_in_km

        # Fall back to getting range from battery
        if status := self._status():
            if status.battery.remaining_cruising_range_in_meters is not None:
                return status.battery.remaining_cruising_range_in_meters / 1000


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
        # If we have disabled the health endpoint, use this as fallback
        elif maint_report := self.vehicle.maintenance.maintenance_report:
            return maint_report.mileage_in_km

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.VEHICLE_HEALTH_INSPECTION]


class InspectionInterval(MySkodaSensor):
    """The number of days before next inspection."""

    entity_description = SensorEntityDescription(
        key="inspection",
        device_class=SensorDeviceClass.DURATION,
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
        device_class=SensorDeviceClass.DURATION,
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


class OutsideTemperature(MySkodaSensor):
    """Measured temperature outside the car."""

    entity_description = SensorEntityDescription(
        key="outside_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        translation_key="outside_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    )

    @property
    def native_value(self) -> float | None:  # noqa: D102
        for source in [self.vehicle.auxiliary_heating, self.vehicle.air_conditioning]:
            if source and (outside_temp := source.outside_temperature):
                temp_value = outside_temp.temperature_value
                if OUTSIDE_TEMP_MIN_BOUND < temp_value < OUTSIDE_TEMP_MAX_BOUND:
                    return temp_value

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.OUTSIDE_TEMPERATURE]
