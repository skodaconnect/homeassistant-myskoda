"""Sensors for the MySkoda integration."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType

from myskoda.models import charging
from myskoda.models.charging import Charging, ChargingStatus
from myskoda.models.info import CapabilityId
from myskoda.myskoda import Health, Status

from .const import COORDINATORS, DOMAIN
from .entity import MySkodaEntity
from .utils import InvalidCapabilityConfigurationError, add_supported_entities


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
            ChargingState,
            LastUpdated,
            MainRender,
            Mileage,
            RemainingChargingTime,
            RemainingDistance,
            SoftwareVersion,
            TargetBatteryPercentage,
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
        name="Software Version",
        icon="mdi:update",
        translation_key="software_version",
    )

    @property
    def native_value(self):  # noqa: D102
        return self.vehicle.info.software_version


class ChargingSensor(MySkodaSensor):
    def _charging(self) -> Charging:
        charging = self.vehicle.charging
        if charging is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )
        return charging

    def _status(self) -> ChargingStatus:
        status = self._charging().status
        if status is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )
        return status

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.CHARGING]


class BatteryPercentage(ChargingSensor):
    """Battery charging state in percent."""

    entity_description = SensorEntityDescription(
        key="battery_percentage",
        name="Battery Percentage",
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
    def native_value(self):  # noqa: D102
        return self._status().battery.state_of_charge_in_percent

    @property
    def icon(self):  # noqa: D102
        suffix = ""

        if self._status().battery.state_of_charge_in_percent >= 95:
            suffix = "100"
        elif self._status().battery.state_of_charge_in_percent >= 85:
            suffix = "90"
        elif self._status().battery.state_of_charge_in_percent >= 75:
            suffix = "80"
        elif self._status().battery.state_of_charge_in_percent >= 65:
            suffix = "70"
        elif self._status().battery.state_of_charge_in_percent >= 55:
            suffix = "60"
        elif self._status().battery.state_of_charge_in_percent >= 45:
            suffix = "50"
        elif self._status().battery.state_of_charge_in_percent >= 35:
            suffix = "40"
        elif self._status().battery.state_of_charge_in_percent >= 25:
            suffix = "30"
        elif self._status().battery.state_of_charge_in_percent >= 15:
            suffix = "20"
        elif self._status().battery.state_of_charge_in_percent >= 5:
            suffix = "10"
        else:
            suffix = "outline"

        if self._status().state != charging.ChargingState.CONNECT_CABLE:
            return f"mdi:battery-charging-{suffix}"
        if suffix == "100":
            return "mdi:battery"
        return f"mdi:battery-{suffix}"


class ChargingPower(ChargingSensor):
    """How fast the car is charging in kW."""

    entity_description = SensorEntityDescription(
        key="charging_power",
        name="Charging Power",
        icon="mdi:lightning-bolt",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        translation_key="charging_power",
    )

    @property
    def native_value(self):  # noqa: D102
        return self._status().charge_power_in_kw


class RemainingDistance(ChargingSensor):
    """Estimated range of an electric vehicle in km."""

    entity_description = SensorEntityDescription(
        key="range",
        name="Range",
        icon="mdi:speedometer",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        translation_key="range",
    )

    @property
    def native_value(self):  # noqa: D102
        return self._status().battery.remaining_cruising_range_in_meters / 1000


class TargetBatteryPercentage(ChargingSensor):
    """Charging target of the EV's battery in percent."""

    entity_description = SensorEntityDescription(
        key="target_battery_percentage",
        name="Target Battery Percentage",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:percent",
        device_class=SensorDeviceClass.BATTERY,
        translation_key="target_battery_percentage",
    )

    @property
    def native_value(self):  # noqa: D102
        return self._charging().settings.target_state_of_charge_in_percent


class Mileage(MySkodaSensor):
    """The vehicle's mileage (total kilometers driven)."""

    entity_description = SensorEntityDescription(
        key="milage",
        name="Milage",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        icon="mdi:counter",
        device_class=SensorDeviceClass.DISTANCE,
        translation_key="milage",
    )

    def _health(self) -> Health:
        health = self.vehicle.health
        if health is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )
        return health

    @property
    def native_value(self):  # noqa: D102
        return self._health().mileage_in_km

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.VEHICLE_HEALTH_INSPECTION]


class ChargeType(ChargingSensor):
    """How the vehicle is being charged (AC/DC)."""

    entity_description = SensorEntityDescription(
        key="charge_type",
        name="Charge Type",
        translation_key="charge_type",
    )

    @property
    def native_value(self):  # noqa: D102
        return self._status().charge_type

    @property
    def icon(self):  # noqa: D102
        if self._status().charge_type == "AC":
            return "mdi:ev-plug-type2"
        return "mdi:ev-plug-ccs2"


class ChargingState(ChargingSensor):
    """Current state of charging (ready, charging, conserving, ...)."""

    entity_description = SensorEntityDescription(
        key="charging_state",
        name="Charging State",
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
    def native_value(self):  # noqa: D102
        return str(self._status().state).lower()

    @property
    def icon(self):  # noqa: D102
        if self._status().state == charging.ChargingState.CONNECT_CABLE:
            return "mdi:power-plug-off"
        if self._status().state == charging.ChargingState.CHARGING:
            return "mdi:power-plug-battery"
        return "mdi:power-plug"


class RemainingChargingTime(ChargingSensor):
    """Estimation on when the vehicle will be fully charged."""

    entity_description = SensorEntityDescription(
        key="remaining_charging_time",
        name="Remaining Charging Time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer",
        translation_key="remaining_charging_time",
    )

    @property
    def native_value(self):  # noqa: D102
        return self._status().remaining_time_to_fully_charged_in_minutes


class LastUpdated(MySkodaSensor):
    """Timestamp of when the car has sent the last update to the MySkoda server."""

    entity_description = SensorEntityDescription(
        key="car_captured",
        name="Last Updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock",
        translation_key="car_captured",
    )

    def _status(self) -> Status:
        status = self.vehicle.status
        if status is None:
            raise InvalidCapabilityConfigurationError(
                self.entity_description.key, self.vehicle
            )
        return status

    @property
    def native_value(self):  # noqa: D102
        return self._status().car_captured_timestamp

    def required_capabilities(self) -> list[CapabilityId]:
        return [CapabilityId.STATE]


class MainRender(MySkodaSensor):
    """URL of the main image render of the vehicle."""

    entity_description = SensorEntityDescription(
        key="render_url_main",
        name="Main Render URL",
        icon="mdi:file-image",
        translation_key="render_url_main",
    )

    @property
    def native_value(self):  # noqa: D102
        return self.get_renders().get("main")
