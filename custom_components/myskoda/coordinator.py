import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass
from datetime import timedelta
import logging
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
from myskoda.models.operation_request import OperationName, OperationStatus
from myskoda.models.user import User
from myskoda.mqtt import EventCharging, EventType

from .const import (
    API_COOLDOWN_IN_SECONDS,
    CONF_POLL_INTERVAL,
    DOMAIN,
    DEFAULT_FETCH_INTERVAL_IN_MINUTES,
)

from . import handle_aiohttp_error

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


@dataclass
class State:
    vehicle: Vehicle
    user: User


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
        self.hass = hass
        self.vin = vin
        self.myskoda = myskoda
        self.config = config
        self.update_driving_range = self._debounce(self._update_driving_range)
        self.update_charging = self._debounce(self._update_charging)
        self.update_air_conditioning = self._debounce(self._update_air_conditioning)
        self.update_vehicle = self._debounce(self._update_vehicle)
        self.update_positions = self._debounce(self._update_positions)

        myskoda.subscribe(self._on_mqtt_event)

    async def _async_update_data(self) -> State:
        vehicle = None
        user = None

        _LOGGER.debug("Performing scheduled update of all data for vin %s", self.vin)
        try:
            vehicle = await self.myskoda.get_vehicle(self.vin)
            user = await self.myskoda.get_user()
        except ClientResponseError as err:
            handle_aiohttp_error("user and vehicle", err, self.hass, self.config)
        except ClientError as err:
            raise UpdateFailed("Error getting update from MySkoda API: %s", err)

        if vehicle and user:
            return State(vehicle, user)
        raise UpdateFailed("Incomplete update received")

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
            OperationName.START_AUXILIARY_HEATING,
            OperationName.STOP_AUXILIARY_HEATING,
        ]:
            await self.update_air_conditioning()
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
        # TODO @webspider: Refactor with proper classes
        vehicle = self.data.vehicle

        data = event.event.data

        if vehicle.charging is None or vehicle.charging.status is None:
            await self.update_charging()
        else:
            status = vehicle.charging.status

            if data.charged_range is not None:
                status.battery.remaining_cruising_range_in_meters = (
                    data.charged_range * 1000
                )
            if data.soc is not None:
                status.battery.state_of_charge_in_percent = data.soc
            if data.time_to_finish is not None:
                status.remaining_time_to_fully_charged_in_minutes = data.time_to_finish
            if data.state is not None:
                status.state = data.state

        if vehicle.driving_range is None:
            await self.update_driving_range()
        else:
            if data.soc is not None:
                vehicle.driving_range.primary_engine_range.current_soc_in_percent = (
                    data.soc
                )
            vehicle.driving_range.primary_engine_range.remaining_range_in_km = (
                data.charged_range
            )

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
        self, func: RefreshFunction, immediate: bool = False
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
