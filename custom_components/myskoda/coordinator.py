import asyncio
import logging
from collections import OrderedDict
from collections.abc import Coroutine
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

from aiohttp import ClientError
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from myskoda import MySkoda, Vehicle
from myskoda.event import (
    Event,
    EventAccess,
    EventAirConditioning,
    EventDeparture,
    EventOperation,
    ServiceEventTopic,
)
from myskoda.models.info import CapabilityId
from myskoda.models.operation_request import OperationName, OperationStatus
from myskoda.models.service_event import (
    ServiceEventChargingData,
    ServiceEventData,
)
from myskoda.models.user import User
from myskoda.mqtt import EventCharging, EventType

from .const import (
    API_COOLDOWN_IN_SECONDS,
    CONF_POLL_INTERVAL,
    DEFAULT_FETCH_INTERVAL_IN_MINUTES,
    DOMAIN,
    MAX_STORED_OPERATIONS,
)
from .error_handlers import handle_aiohttp_error

_LOGGER = logging.getLogger(__name__)

type RefreshFunction = Callable[[], Coroutine[None, None, None]]


class MySkodaDebouncer(Debouncer):
    """Class to rate limit calls to MySkoda REST APIs."""

    def __init__(
        self, hass: HomeAssistant, func: RefreshFunction, immediate: bool
    ) -> None:
        """Initialize debounce."""

        self.immediate = immediate

        super().__init__(
            hass,
            _LOGGER,
            cooldown=API_COOLDOWN_IN_SECONDS,
            immediate=immediate,
            function=func,
        )


# History of EventType.OPERATION events, keyed by request_id
Operations = OrderedDict[str, EventOperation]


@dataclass
class Config:
    auxiliary_heater_duration: float | None = None


@dataclass
class State:
    vehicle: Vehicle
    user: User
    config: Config
    operations: Operations


class MySkodaDataUpdateCoordinator(DataUpdateCoordinator[State]):
    """See `DataUpdateCoordinator`.

    This class manages all data from the MySkoda API.
    """

    data: State

    def __init__(
        self, hass: HomeAssistant, config: ConfigEntry, myskoda: MySkoda, vin: str
    ) -> None:
        """Create a new coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=config.options.get(
                    CONF_POLL_INTERVAL, DEFAULT_FETCH_INTERVAL_IN_MINUTES
                )
            ),
            always_update=False,
        )
        self.hass: HomeAssistant = hass
        self.vin: str = vin
        self.myskoda: MySkoda = myskoda
        self.operations: OrderedDict = OrderedDict()
        self.config: ConfigEntry = config
        self.update_driving_range = self._debounce(self._update_driving_range)
        self.update_charging = self._debounce(self._update_charging)
        self.update_air_conditioning = self._debounce(self._update_air_conditioning)
        self.update_auxiliary_heating = self._debounce(self._update_auxiliary_heating)
        self.update_vehicle = self._debounce(self._update_vehicle)
        self.update_positions = self._debounce(self._update_positions)
        self._mqtt_connecting: bool = False

    async def _async_update_data(self) -> State:
        vehicle = None
        user = None
        config = self.data.config if self.data and self.data.config else Config()
        operations = self.operations

        if not self.myskoda.mqtt and not self._mqtt_connecting:
            self.hass.async_create_task(self._mqtt_connect())

        _LOGGER.debug("Performing scheduled update of all data for vin %s", self.vin)

        # Obtain user data. This is allowed to fail if we already have this in state.
        try:
            user = await self.myskoda.get_user()
        except ClientResponseError as err:
            handle_aiohttp_error("user", err, self.hass, self.config)
            if self.data.user:
                user = self.data.user
            else:
                raise UpdateFailed("Error getting user data from MySkoda API: %s", err)

        # Obtain vehicle data.
        try:
            if self.data:
                if (
                    self.data.vehicle.info.device_platform == "MBB"
                    and self.data.vehicle.info.specification.model == "CitigoE iV"
                ):
                    _LOGGER.debug(
                        "Detected CitigoE iV, requesting only partial update without health"
                    )
                    vehicle = await self.myskoda.get_partial_vehicle(
                        self.vin,
                        [
                            CapabilityId.AIR_CONDITIONING,
                            CapabilityId.AUXILIARY_HEATING,
                            CapabilityId.CHARGING,
                            CapabilityId.PARKING_POSITION,
                            CapabilityId.STATE,
                            CapabilityId.TRIP_STATISTICS,
                        ],
                    )
                else:
                    vehicle = await self.myskoda.get_vehicle(self.vin)
            else:
                vehicle = await self.myskoda.get_vehicle(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("vehicle", err, self.hass, self.config)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if vehicle and user:
            return State(vehicle, user, config, operations)
        raise UpdateFailed("Incomplete update received")

    async def _mqtt_connect(self) -> None:
        """Connect to MQTT and handle internals."""
        _LOGGER.debug("Connecting to MQTT.")
        self._mqtt_connecting = True
        await self.myskoda.enable_mqtt()
        self.myskoda.subscribe(self._on_mqtt_event)
        self._mqtt_connecting = False

    async def _on_mqtt_event(self, event: Event) -> None:
        if event.vin != self.vin:
            return

        if event.type == EventType.OPERATION:
            await self._on_operation_event(event)
        if event.type == EventType.SERVICE_EVENT:
            if event.topic == ServiceEventTopic.CHARGING:
                await self._on_charging_event(event)
            if event.topic == ServiceEventTopic.ACCESS:
                await self._on_access_event(event)
            if event.topic == ServiceEventTopic.AIR_CONDITIONING:
                await self._on_air_conditioning_event(event)
            if event.topic == ServiceEventTopic.DEPARTURE:
                await self._on_departure_event(event)

    async def _on_operation_event(self, event: EventOperation) -> None:
        # Store the last MAX_STORED_OPERATIONS operations
        if request_id := event.operation.request_id:
            self.operations[request_id] = event
            while len(self.operations) > MAX_STORED_OPERATIONS:
                self.operations.popitem(last=False)
            self.async_set_updated_data(self.data)

        if event.operation.status == OperationStatus.IN_PROGRESS:
            return
        if event.operation.status == OperationStatus.ERROR:
            _LOGGER.error(
                "Error received from car in operation %s, reason: %s. Requesting MySkoda full update",
                event.operation.status,
                event.operation.error_code,
            )
            await self.update_vehicle()
            return
        if event.operation.operation in [
            OperationName.STOP_AIR_CONDITIONING,
            OperationName.START_AIR_CONDITIONING,
            OperationName.SET_AIR_CONDITIONING_TARGET_TEMPERATURE,
            OperationName.START_WINDOW_HEATING,
            OperationName.STOP_WINDOW_HEATING,
        ]:
            await self.update_air_conditioning()
        if event.operation.operation in [
            OperationName.START_AUXILIARY_HEATING,
            OperationName.STOP_AUXILIARY_HEATING,
        ]:
            await self.update_auxiliary_heating()
        if event.operation.operation in [
            OperationName.UPDATE_CHARGE_LIMIT,
            OperationName.UPDATE_CARE_MODE,
            OperationName.UPDATE_CHARGING_CURRENT,
            OperationName.START_CHARGING,
            OperationName.STOP_CHARGING,
        ]:
            await self.update_charging()
        if event.operation.operation in [
            OperationName.LOCK,
            OperationName.UNLOCK,
        ]:
            await self.update_status(immediate=True)

    async def _on_charging_event(self, event: EventCharging):
        vehicle = self.data.vehicle
        update_charging_request_sent = False
        if vehicle.charging is None or vehicle.charging.status is None:
            await self.update_charging()
            update_charging_request_sent = True
        if vehicle.driving_range is None:
            await self.update_driving_range()

        event_data = event.event.data
        match event_data:
            case ServiceEventChargingData():
                if vehicle.charging and (status := vehicle.charging.status):
                    status.battery.remaining_cruising_range_in_meters = (
                        event_data.charged_range * 1000
                    )
                    status.battery.state_of_charge_in_percent = event_data.soc
                    if event_data.time_to_finish is not None:
                        status.remaining_time_to_fully_charged_in_minutes = (
                            event_data.time_to_finish
                        )
                        status.state = event_data.state
                if vehicle.driving_range:
                    vehicle.driving_range.primary_engine_range.current_soc_in_percent = event_data.soc
                    vehicle.driving_range.primary_engine_range.remaining_range_in_km = (
                        event_data.charged_range
                    )
                self.set_updated_vehicle(vehicle)
            case ServiceEventData():
                if not update_charging_request_sent:
                    await self.update_charging()

    async def _on_access_event(self, event: EventAccess):
        await self.update_vehicle()

    async def _on_air_conditioning_event(self, event: EventAirConditioning):
        await self.update_air_conditioning()

    async def _on_departure_event(self, event: EventDeparture):
        await self.update_positions()

    def _unsub_refresh(self):
        return

    def set_updated_vehicle(self, vehicle: Vehicle) -> None:
        self.data.vehicle = vehicle
        self.async_set_updated_data(self.data)

    async def _update_driving_range(self) -> None:
        driving_range = None

        _LOGGER.debug("Updating driving range for %s", self.vin)
        try:
            driving_range = await self.myskoda.get_driving_range(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("driving range", err, self.hass, self.config)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if driving_range:
            vehicle = self.data.vehicle
            vehicle.driving_range = driving_range
            self.set_updated_vehicle(vehicle)

    async def _update_charging(self) -> None:
        charging = None

        _LOGGER.debug("Updating charging information for %s", self.vin)
        try:
            charging = await self.myskoda.get_charging(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("charging information", err, self.hass, self.config)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if charging:
            vehicle = self.data.vehicle
            vehicle.charging = charging
            self.set_updated_vehicle(vehicle)

    async def _update_air_conditioning(self) -> None:
        air_conditioning = None

        _LOGGER.debug("Updating air conditioning for %s", self.vin)
        try:
            air_conditioning = await self.myskoda.get_air_conditioning(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("AC update", err, self.hass, self.config)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if air_conditioning:
            vehicle = self.data.vehicle
            vehicle.air_conditioning = air_conditioning
            self.set_updated_vehicle(vehicle)

    async def _update_auxiliary_heating(self) -> None:
        # PHEV vehicles are not using auxiliary_heating endpoint, but air_conditioning instead
        if not self.data.vehicle.has_capability(CapabilityId.AUXILIARY_HEATING):
            await self.update_air_conditioning()
            return

        auxiliary_heating = None

        _LOGGER.debug("Updating auxiliary heating for %s", self.vin)
        try:
            auxiliary_heating = await self.myskoda.get_auxiliary_heating(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("Auxiliary update", err, self.hass, self.config)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if auxiliary_heating:
            vehicle = self.data.vehicle
            vehicle.auxiliary_heating = auxiliary_heating
            self.set_updated_vehicle(vehicle)

    async def _update_status(self) -> None:
        status = None

        _LOGGER.debug("Updating vehicle status for %s", self.vin)
        try:
            status = await self.myskoda.get_status(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("vehicle status", err, self.hass, self.config)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if status:
            vehicle = self.data.vehicle
            vehicle.status = status
            self.set_updated_vehicle(vehicle)

    async def _update_vehicle(self) -> None:
        vehicle = None

        _LOGGER.debug("Updating full vehicle for %s", self.vin)
        try:
            vehicle = await self.myskoda.get_vehicle(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("vehicle update", err, self.hass, self.config)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if vehicle:
            self.set_updated_vehicle(vehicle)

    def _debounce(
        self, func: RefreshFunction, immediate: bool = True
    ) -> RefreshFunction:
        return MySkodaDebouncer(self.hass, func, immediate).async_call

    async def _update_positions(self) -> None:
        positions = None
        _LOGGER.debug("Updating positions for %s", self.vin)
        try:
            await asyncio.sleep(60)  # GPS is not updated immediately, wait 60 seconds
            positions = await self.myskoda.get_positions(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("positions", err, self.hass, self.config)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if positions:
            vehicle = self.data.vehicle
            vehicle.positions = positions
            self.set_updated_vehicle(vehicle)

    async def update_status(self, immediate: bool = False) -> RefreshFunction:
        return self._debounce(self._update_status, immediate)
