import asyncio
import logging
from collections import OrderedDict, deque
from collections.abc import Coroutine
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

from aiohttp import ClientError
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from myskoda import MySkoda, Vehicle
from myskoda.event import (
    Event,
    EventAccess,
    EventAirConditioning,
    EventDeparture,
    EventOperation,
    ServiceEvent,
    ServiceEventTopic,
)
from myskoda.models.info import CapabilityId
from myskoda.models.operation_request import OperationName, OperationStatus
from myskoda.models.user import User
from myskoda.mqtt import EventCharging, EventType

from .const import (
    API_COOLDOWN_IN_SECONDS,
    CONF_POLL_INTERVAL,
    COORDINATORS,
    DEFAULT_FETCH_INTERVAL_IN_MINUTES,
    DOMAIN,
    MAX_STORED_OPERATIONS,
    MAX_STORED_SERVICE_EVENTS,
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


# History of EventType.SERVICE_EVENT events
ServiceEvents = deque[ServiceEvent]


@dataclass
class Config:
    auxiliary_heater_duration: float | None = None


@dataclass
class State:
    vehicle: Vehicle
    user: User
    config: Config
    operations: Operations
    service_events: ServiceEvents


class MySkodaDataUpdateCoordinator(DataUpdateCoordinator[State]):
    """See `DataUpdateCoordinator`.

    This class manages all data from the MySkoda API.
    """

    data: State

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, myskoda: MySkoda, vin: str
    ) -> None:
        """Create a new coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=entry.options.get(
                    CONF_POLL_INTERVAL, DEFAULT_FETCH_INTERVAL_IN_MINUTES
                )
            ),
            always_update=False,
        )
        self.hass: HomeAssistant = hass
        self.vin: str = vin
        self.myskoda: MySkoda = myskoda
        self.operations: OrderedDict = OrderedDict()
        self.service_events: deque = deque(maxlen=MAX_STORED_SERVICE_EVENTS)
        self.entry: ConfigEntry = entry
        self.update_driving_range = self._debounce(self._update_driving_range)
        self.update_charging = self._debounce(self._update_charging)
        self.update_air_conditioning = self._debounce(self._update_air_conditioning)
        self.update_auxiliary_heating = self._debounce(self._update_auxiliary_heating)
        self.update_vehicle = self._debounce(self._update_vehicle)
        self.update_positions = self._debounce(self._update_positions)
        self.update_departure_info = self._debounce(self._update_departure_info)
        self._mqtt_connecting: bool = False

    async def _async_get_minimal_data(self) -> Vehicle:
        """Internal method that fetches only basic vehicle info."""
        return await self.myskoda.get_partial_vehicle(self.vin, [])

    async def _async_get_vehicle_data(self) -> Vehicle:
        """Internal method that fetches vehicle data."""
        if self.data:
            if (
                self.data.vehicle.info.device_platform == "MBB"
                and self.data.vehicle.info.specification.model == "CitigoE iV"
            ):
                _LOGGER.debug(
                    "Detected Citigo iV, requesting only partial update without health"
                )
                vehicle = await self.myskoda.get_partial_vehicle(
                    self.vin,
                    [
                        CapabilityId.AIR_CONDITIONING,
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
        return vehicle

    async def _async_update_data(self) -> State:
        vehicle = None
        user = None
        config = self.data.config if self.data and self.data.config else Config()
        operations = self.operations
        service_events = self.service_events

        if self.entry.state == ConfigEntryState.SETUP_IN_PROGRESS:
            if getattr(self, "_startup_called", False):
                return self.data  # Prevent duplicate execution
            _LOGGER.debug("Performing initial data fetch for vin %s", self.vin)
            try:
                user = await self.myskoda.get_user()
                vehicle = await self._async_get_minimal_data()
                self._startup_called = True  # Prevent duplicate execution
            except ClientResponseError as err:
                handle_aiohttp_error(
                    "setup user and vehicle", err, self.hass, self.entry
                )
                raise UpdateFailed("Failed to retrieve initial data during setup")

            async def _async_finish_startup(hass: HomeAssistant) -> None:
                """Tasks to execute when we have finished starting up."""
                _LOGGER.debug(
                    "MySkoda has finished starting up. Scheduling post-start tasks for vin %s.",
                    self.vin,
                )
                try:
                    coord = hass.data[DOMAIN][self.entry.entry_id][COORDINATORS][
                        self.vin
                    ]
                    if not coord.myskoda.mqtt and not coord._mqtt_connecting:
                        self.entry.async_create_background_task(
                            self.hass, coord._mqtt_connect(), "mqtt"
                        )
                except KeyError:
                    _LOGGER.debug("Could not connect to MQTT. Waiting for regular poll")
                    pass

            async_at_started(
                hass=self.hass, at_start_cb=_async_finish_startup
            )  # Schedule post-setup tasks
            return State(vehicle, user, config, operations, service_events)

        # Regular update

        _LOGGER.debug("Performing scheduled update of all data for vin %s", self.vin)

        # Obtain user data. This is allowed to fail if we already have this in state.
        try:
            user = await self.myskoda.get_user()
        except ClientResponseError as err:
            handle_aiohttp_error("user", err, self.hass, self.entry)
            if self.data.user:
                user = self.data.user
            else:
                raise UpdateFailed("Error getting user data from MySkoda API: %s", err)

        # Obtain vehicle data.
        try:
            vehicle = await self._async_get_vehicle_data()
        except ClientResponseError as err:
            handle_aiohttp_error("vehicle", err, self.hass, self.entry)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if vehicle and user:
            return State(vehicle, user, config, operations, service_events)
        raise UpdateFailed("Incomplete update received")

    async def _mqtt_connect(self) -> None:
        """Connect to MQTT and handle internals."""
        _LOGGER.debug("Connecting to MQTT.")
        self._mqtt_connecting = True
        try:
            await self.myskoda.enable_mqtt()
            self.myskoda.subscribe(self._on_mqtt_event)
        except Exception:
            pass
        self._mqtt_connecting = False

    async def _on_mqtt_event(self, event: Event) -> None:
        if event.vin != self.vin:
            return

        if event.type == EventType.OPERATION:
            await self._on_operation_event(event)
        if event.type == EventType.SERVICE_EVENT:
            # Store the event and update data
            self.service_events.appendleft(event.event)
            self.async_set_updated_data(self.data)

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
            OperationName.SET_AIR_CONDITIONING_TIMERS,
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
            OperationName.UPDATE_AUTO_UNLOCK_PLUG,
        ]:
            await self.update_charging()
        if event.operation.operation in [
            OperationName.LOCK,
            OperationName.UNLOCK,
        ]:
            await self.update_status(immediate=True)
        if event.operation.operation in [
            OperationName.UPDATE_DEPARTURE_TIMERS,
        ]:
            await self.update_departure_info()

    async def _on_charging_event(self, event: EventCharging):
        vehicle = self.data.vehicle
        update_charging_request_sent = False
        if vehicle.charging is None or vehicle.charging.status is None:
            await self.update_charging()
            update_charging_request_sent = True
        if vehicle.driving_range is None:
            await self.update_driving_range()

        event_data = event.event.data
        if vehicle.charging and (status := vehicle.charging.status):
            if event_data.charged_range:
                status.battery.remaining_cruising_range_in_meters = (
                    event_data.charged_range * 1000
                )
            if event_data.soc:
                status.battery.state_of_charge_in_percent = event_data.soc
            if event_data.time_to_finish:
                status.remaining_time_to_fully_charged_in_minutes = (
                    event_data.time_to_finish
                )
            if event_data.state:
                status.state = event_data.state
        if vehicle.driving_range:
            if event_data.soc:
                vehicle.driving_range.primary_engine_range.current_soc_in_percent = (
                    event_data.soc
                )
            if event_data.charged_range:
                vehicle.driving_range.primary_engine_range.remaining_range_in_km = (
                    event_data.charged_range
                )
        some_charging_data_missing = (
            event_data.charged_range is None
            or event_data.soc is None
            or event_data.state is None
        )
        if some_charging_data_missing and not update_charging_request_sent:
            # After update is done, the set_updated_vehicle is called there
            await self.update_charging()
        else:
            self.set_updated_vehicle(vehicle)

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
            handle_aiohttp_error("driving range", err, self.hass, self.entry)
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
            handle_aiohttp_error("charging information", err, self.hass, self.entry)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if charging:
            vehicle = self.data.vehicle
            vehicle.charging = charging
            # Update driving range similarly to the received charging service event
            if vehicle.driving_range and charging.status:
                vehicle.driving_range.primary_engine_range.current_soc_in_percent = (
                    charging.status.battery.state_of_charge_in_percent
                )
                vehicle.driving_range.primary_engine_range.remaining_range_in_km = (
                    charging.status.battery.remaining_cruising_range_in_meters
                )
            self.set_updated_vehicle(vehicle)

    async def _update_air_conditioning(self) -> None:
        air_conditioning = None

        _LOGGER.debug("Updating air conditioning for %s", self.vin)
        try:
            air_conditioning = await self.myskoda.get_air_conditioning(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("AC update", err, self.hass, self.entry)
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
            handle_aiohttp_error("Auxiliary update", err, self.hass, self.entry)
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
            handle_aiohttp_error("vehicle status", err, self.hass, self.entry)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if status:
            vehicle = self.data.vehicle
            vehicle.status = status
            self.set_updated_vehicle(vehicle)

    async def _update_departure_info(self) -> None:
        departure_info = None

        _LOGGER.debug("Updating departure info for %s", self.vin)
        try:
            departure_info = await self.myskoda.get_departure_timers(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("departure info", err, self.hass, self.entry)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if departure_info:
            vehicle = self.data.vehicle
            vehicle.departure_info = departure_info
            self.set_updated_vehicle(vehicle)

    async def _update_vehicle(self) -> None:
        vehicle = None

        _LOGGER.debug("Updating full vehicle for %s", self.vin)
        try:
            vehicle = await self.myskoda.get_vehicle(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("vehicle update", err, self.hass, self.entry)
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
            handle_aiohttp_error("positions", err, self.hass, self.entry)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if positions:
            vehicle = self.data.vehicle
            vehicle.positions = positions
            self.set_updated_vehicle(vehicle)

    async def update_status(self, immediate: bool = False) -> RefreshFunction:
        return self._debounce(self._update_status, immediate)
