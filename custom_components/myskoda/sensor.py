"""Sensors for the MySkoda integration."""

from datetime import UTC, datetime
from math import isnan

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
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
from myskoda.models.event import OperationStatus
from myskoda.models.info import CapabilityId

from .const import COORDINATORS, DOMAIN, OUTSIDE_TEMP_MAX_BOUND, OUTSIDE_TEMP_MIN_BOUND
from .coordinator import MySkodaConfigEntry
from .entity import MySkodaEntity
from .utils import add_supported_entities


async def async_setup_entry(
    hass: HomeAssistant,
    config: MySkodaConfigEntry,
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
            GasRange,
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
            ServiceEvent,
            SoftwareVersion,
            TargetBatteryPercentage,
            ClimatisationTimeLeft,
            AuxHeaterTimeLeft,
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
            return last_operation.status.lower()

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
                "request_id": event.request_id,
                "operation": event.operation,
                "status": event.status.lower(),
                "error_code": event.error_code,
                "timestamp": event.timestamp,
            }
            for event in operations
        ]
        attributes = filtered[0]
        attributes["history"] = filtered[1:]

        return attributes


class ServiceEvent(MySkodaSensor):
    """Report the most recent service event."""

    entity_description = SensorEntityDescription(
        key="service_event",
        translation_key="service_event",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    @property
    def native_value(self) -> datetime | None:
        """Returns the timestamp of the last seen service event."""
        if self.service_events:
            last_service_event = self.service_events[0]
            return last_service_event.timestamp

    @property
    def extra_state_attributes(self) -> dict:
        """Returns additional attributes for the service event sensor.

        - history: a list of dicts with the same fields for the previously seen event.
        """
        attributes = {}
        if not self.service_events:
            return attributes

        filtered = [
            {
                "name": event.name.value,
                "timestamp": event.timestamp,
                "data": event.data,
            }
            for event in self.service_events
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
            if status.battery.state_of_charge_in_percent is not None:
                return min(status.battery.state_of_charge_in_percent, 100)

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

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING, CapabilityId.EXTENDED_CHARGING_SETTINGS]


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
        if driving_range := self.vehicle.driving_range:
            if driving_range.ad_blue_range is not None:
                return driving_range.ad_blue_range

    @property
    def available(self) -> bool:
        """Determine whether the sensor is available."""
        if driving_range := self.vehicle.driving_range:
            return driving_range.ad_blue_range is not None
        return False

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE, CapabilityId.FUEL_STATUS]

    def forbidden_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING]


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
        if driving_range := self.vehicle.driving_range:
            if primary := driving_range.primary_engine_range:
                if primary.engine_type in [EngineType.GASOLINE, EngineType.DIESEL]:
                    return primary.remaining_range_in_km
            if secondary := driving_range.secondary_engine_range:
                if secondary.engine_type in [EngineType.GASOLINE, EngineType.DIESEL]:
                    return secondary.remaining_range_in_km

    @property
    def available(self) -> bool:
        if driving_range := self.vehicle.driving_range:
            return driving_range.car_type == EngineType.HYBRID
        return False

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE, CapabilityId.FUEL_STATUS]

    def forbidden_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING_MEB]


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
        if driving_range := self.vehicle.driving_range:
            if driving_range.secondary_engine_range is not None:
                return driving_range.secondary_engine_range.remaining_range_in_km

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
        if driving_range := self.vehicle.driving_range:
            if driving_range.primary_engine_range is not None:
                return driving_range.primary_engine_range.remaining_range_in_km

    @property
    def available(self) -> bool:
        if driving_range := self.vehicle.driving_range:
            return (
                driving_range.car_type in (EngineType.HYBRID, EngineType.CNG)
                and (primary_engine_range := driving_range.primary_engine_range)
                and primary_engine_range.engine_type == EngineType.CNG
            )
        return False

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE, CapabilityId.FUEL_STATUS]

    def forbidden_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING]


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
        if driving_range := self.vehicle.driving_range:
            return driving_range.primary_engine_range.current_fuel_level_in_percent

    @property
    def available(self) -> bool:
        if driving_range := self.vehicle.driving_range:
            return (
                driving_range.car_type in (EngineType.HYBRID, EngineType.CNG)
                and (primary_engine_range := driving_range.primary_engine_range)
                and primary_engine_range.engine_type == EngineType.CNG
            )
        return False

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE, CapabilityId.FUEL_STATUS]

    def forbidden_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING]


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
        if driving_range := self.vehicle.driving_range:
            if primary := driving_range.primary_engine_range:
                if primary.engine_type in [EngineType.GASOLINE, EngineType.DIESEL]:
                    return primary.current_fuel_level_in_percent
            if secondary := driving_range.secondary_engine_range:
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

    @property
    def available(self) -> bool:
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
        if driving_range := self.vehicle.driving_range:
            return driving_range.total_range_in_km

        # Fall back to getting range from battery
        if status := self._status():
            if status.battery.remaining_cruising_range_in_meters is not None:
                return status.battery.remaining_cruising_range_in_meters / 1000

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE]


class TargetBatteryPercentage(ChargingSensor):
    """Charging target of the EV's battery in percent."""

    entity_description = SensorEntityDescription(
        key="target_battery_percentage",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        translation_key="target_battery_percentage",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if charging := self._charging():
            return charging.settings.target_state_of_charge_in_percent

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING, CapabilityId.EXTENDED_CHARGING_SETTINGS]


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
        """Calculate the mileage_in_km.

        The API sometimes erroneously returns an old, lower value. Mileage should never go down.
        To work around this we inspect the last state, if there is one, and return that if it is
        larger than the value from the API.

        The API also sometimes erroneously returns the value 429_496_729. Values over 400_000_000
        are ignored and the last value is returned instead, if there is one.
        """
        last_value = 0
        last_state = self.hass.states.get(self.entity_id)
        if last_state and last_state.state:
            try:
                last_value = int(last_state.state)
            except (ValueError, TypeError):
                pass  # value may initially be 'unavailable' or 'None'

        def _valid_km(value):
            return isinstance(value, int) and not isnan(value)

        mileage_in_km = None
        if (maintenance := self.vehicle.maintenance) and (
            report := maintenance.maintenance_report
        ):
            if _valid_km(report.mileage_in_km):
                mileage_in_km = report.mileage_in_km

        # If the maint report does not have mileage, use vehicle health as fallback
        if (
            mileage_in_km is None
            and (health := self.vehicle.health)
            and _valid_km(health.mileage_in_km)
        ):
            mileage_in_km = health.mileage_in_km

        if mileage_in_km and mileage_in_km < 400_000_000:
            return max(mileage_in_km, last_value)
        return last_value if last_value else None


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
        return [CapabilityId.FUEL_STATUS]


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
        return [CapabilityId.FUEL_STATUS]


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
            if status.state != charging.ChargingState.CONNECT_CABLE:
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

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING, CapabilityId.EXTENDED_CHARGING_SETTINGS]


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


class ClimatisationTimeLeft(MySkodaSensor):
    """Estimated time left until climatisation via AC has reached its goal."""

    entity_description = SensorEntityDescription(
        key="estimated_time_left_to_reach_target_temperature",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.MINUTES,
        translation_key="estimated_time_left_to_reach_target_temperature",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if _ac := self.vehicle.air_conditioning:
            if _ac.estimated_date_time_to_reach_target_temperature:
                target_datetime = _ac.estimated_date_time_to_reach_target_temperature
                now = datetime.now(UTC)

                duration = target_datetime - now

                # If we reached it already, return 0
                return max(0, int(duration.total_seconds()))

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AIR_CONDITIONING]


class AuxHeaterTimeLeft(MySkodaSensor):
    """Estimated time left until climatisation via aux heater has reached its goal."""

    entity_description = SensorEntityDescription(
        key="aux_estimated_time_left_to_reach_target_temperature",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.MINUTES,
        translation_key="aux_estimated_time_left_to_reach_target_temperature",
    )

    @property
    def native_value(self) -> int | None:  # noqa: D102
        if _aux := self.vehicle.auxiliary_heating:
            if target_datetime := _aux.estimated_date_time_to_reach_target_temperature:
                now = datetime.now(UTC)

                duration = target_datetime - now

                # If we reached it already, return 0
                return max(0, int(duration.total_seconds()))

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.AUXILIARY_HEATING]
