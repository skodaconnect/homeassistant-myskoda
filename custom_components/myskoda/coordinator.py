"""Coordinator for the MySkoda integration."""

import logging
from collections import OrderedDict, deque
from collections.abc import Coroutine
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

from aiohttp import ClientError
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from myskoda import MySkoda, Vehicle
from myskoda.models.event import BaseEvent, OperationEvent, ServiceEvent
from myskoda.models.user import User

from .const import (
    API_COOLDOWN_IN_SECONDS,
    CONF_POLL_INTERVAL,
    COORDINATORS,
    DEFAULT_FETCH_INTERVAL_IN_MINUTES,
    DOMAIN,
    MAX_STORED_OPERATIONS,
    MAX_STORED_SERVICE_EVENTS,
    MQTT_RECONNECT_INTERVAL_IN_SECONDS,
)
from .error_handlers import handle_aiohttp_error

_LOGGER = logging.getLogger(__name__)

type RefreshFunction = Callable[[], Coroutine[None, None, None]]
type MySkodaConfigEntry = ConfigEntry[MySkodaDataUpdateCoordinator]


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
Operations = OrderedDict[str, OperationEvent]


# History of EventType.SERVICE_EVENT events
ServiceEvents = deque[ServiceEvent]


@dataclass
class Config:
    """Custom configuration."""

    auxiliary_heater_duration: float | None = None


@dataclass
class State:
    """Data managed by the coordinator."""

    vehicle: Vehicle
    user: User
    config: Config
    operations: Operations
    service_events: ServiceEvents


class MySkodaDataUpdateCoordinator(DataUpdateCoordinator[State]):
    """Coordinator for the MySkoda integration.

    This class manages all data from the MySkoda API.
    """

    data: State

    def __init__(
        self, hass: HomeAssistant, entry: MySkodaConfigEntry, myskoda: MySkoda, vin: str
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
        self.myskoda.subscribe_updates(vin, self._on_myskoda_update)
        self.operations: OrderedDict = OrderedDict()
        self.service_events: deque = deque(maxlen=MAX_STORED_SERVICE_EVENTS)
        self.entry: MySkodaConfigEntry = entry
        self._mqtt_connecting: bool = False
        self._mqtt_retry_scheduled: bool = False
        self._startup_called: bool = False

    async def _async_update_data(self) -> State:
        """Called by parent class during setup and scheduled refresh."""
        config = self.data.config if self.data and self.data.config else Config()

        if self.entry.state == ConfigEntryState.SETUP_IN_PROGRESS:
            if getattr(self, "_startup_called", False):
                return self.data  # Prevent duplicate execution
            _LOGGER.debug("Performing initial data fetch for vin %s", self.vin)
            try:
                user = await self.myskoda.get_user()
                vehicle = await self.myskoda.get_partial_vehicle(self.vin, [])
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

                async def _retry_mqtt(_now=None) -> None:
                    """Retry loop for MQTT connection."""
                    if not self.myskoda.mqtt and not self._mqtt_connecting:
                        await self._mqtt_connect()
                    if not self.myskoda.mqtt and not self._mqtt_retry_scheduled:
                        _LOGGER.warning(
                            "Could not connect to MQTT. Retry in %s seconds",
                            MQTT_RECONNECT_INTERVAL_IN_SECONDS,
                        )
                        async_call_later(
                            hass, MQTT_RECONNECT_INTERVAL_IN_SECONDS, _retry_mqtt
                        )
                        self._mqtt_retry_scheduled = True
                        return
                    self._mqtt_retry_scheduled = False

                try:
                    coord = hass.data[DOMAIN][self.entry.entry_id][COORDINATORS][
                        self.vin
                    ]
                    if not coord.myskoda.mqtt and not coord._mqtt_connecting:
                        self.entry.async_create_background_task(
                            self.hass, coord._mqtt_connect(), "mqtt"
                        )
                except KeyError:
                    if not self._mqtt_retry_scheduled:
                        _LOGGER.warning(
                            "Could not connect to MQTT. Retry in %s seconds",
                            MQTT_RECONNECT_INTERVAL_IN_SECONDS,
                        )
                        async_call_later(
                            hass, MQTT_RECONNECT_INTERVAL_IN_SECONDS, _retry_mqtt
                        )
                        self._mqtt_retry_scheduled = True

            async_at_started(
                hass=self.hass, at_start_cb=_async_finish_startup
            )  # Schedule post-setup tasks
            return State(vehicle, user, config, self.operations, self.service_events)

        # Regular update
        _LOGGER.debug("Performing scheduled refresh of all data for vin %s", self.vin)

        # Refresh user data. This is allowed to fail if we already have this in state.
        try:
            await self.myskoda.refresh_user()
        except ClientResponseError as err:
            handle_aiohttp_error("user", err, self.hass, self.entry)
            if not self.data.user:
                raise UpdateFailed(
                    f"Error getting user data from MySkoda API: {err}"
                ) from err

        # Refresh vehicle data.
        try:
            await self.myskoda.refresh_vehicle(self.vin)
        except ClientResponseError as err:
            handle_aiohttp_error("vehicle", err, self.hass, self.entry)
        except ClientError as err:
            raise UpdateFailed(f"Error getting update from MySkoda API: {err}") from err

        return State(
            self.data.vehicle,
            self.data.user,
            self.data.config,
            self.operations,
            self.service_events,
        )

    async def _on_myskoda_update(self) -> None:
        """Trigger an update of all HA entities when User or Vehicle change.

        Always pass in a copy of the object to force an update.
        """
        _LOGGER.debug("Received update notification for %s", self.vin)
        if user := deepcopy(self.myskoda.user):
            self.data.user = user
        self.data.vehicle = deepcopy(self.myskoda.vehicle(self.vin))
        self.async_set_updated_data(self.data)

    async def _mqtt_connect(self) -> None:
        """Connect to MQTT and handle internals."""
        _LOGGER.debug("Connecting to MQTT.")
        self._mqtt_connecting = True
        try:
            await self.myskoda.enable_mqtt()
            self.myskoda.subscribe_events(self._on_mqtt_event)
        except Exception:
            pass
        self._mqtt_connecting = False

    async def _on_mqtt_event(self, event: BaseEvent) -> None:
        if event.vin != self.vin:
            return
        if isinstance(event, OperationEvent):
            # Store the last MAX_STORED_OPERATIONS operations
            if request_id := event.request_id:
                self.operations[request_id] = event
                while len(self.operations) > MAX_STORED_OPERATIONS:
                    self.operations.popitem(last=False)
        if isinstance(event, ServiceEvent):
            self.service_events.appendleft(event)
        self.async_set_updated_data(self.data)

    def _unsub_refresh(self):
        return
