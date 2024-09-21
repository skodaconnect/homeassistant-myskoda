from collections.abc import Coroutine
from datetime import timedelta
import logging
from typing import Awaitable, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.ssl import get_default_context
from myskoda import MySkoda, Vehicle
from myskoda.event import (
    Event,
    EventAccess,
    EventAirConditioning,
    EventOperation,
    ServiceEventTopic,
)
from myskoda.models.operation_request import OperationName, OperationStatus
from myskoda.models.user import User
from myskoda.mqtt import EventCharging, EventType

from .const import DOMAIN, FETCH_INTERVAL_IN_MINUTES, API_COOLDOWN_IN_SECONDS

_LOGGER = logging.getLogger(__name__)

type RefreshFunctionVin = Callable[[str], Coroutine[None, None, None]]
type RefreshFunction = Callable[[], Coroutine[None, None, None]]


class MySkodaDebouncer[T](Debouncer):
    """Class to rate limit calls to MySkoda REST APIs."""

    def __init__(
        self, hass: HomeAssistant, vin: str, func: Callable[[str], Awaitable[T]]
    ) -> None:
        """Initialize debounce."""

        async def call_func() -> None:
            await func(vin)

        super().__init__(
            hass,
            _LOGGER,
            cooldown=API_COOLDOWN_IN_SECONDS,
            immediate=False,
            function=call_func,
        )


class State:
    vehicles: dict[str, Vehicle]
    user: User

    def __init__(self, vehicles: list[Vehicle], user: User) -> None:
        self.vehicles = {}
        for vehicle in vehicles:
            self.vehicles[vehicle.info.vin] = vehicle
        self.user = user


class DebouncedRefresh:
    update_driving_range: RefreshFunction
    update_charging: RefreshFunction
    update_air_conditioning: RefreshFunction
    update_vehicle: RefreshFunction

    def __init__(
        self,
        hass: HomeAssistant,
        vin: str,
        update_driving_range: RefreshFunctionVin,
        update_charging: RefreshFunctionVin,
        update_air_conditioning: RefreshFunctionVin,
        update_vehicle: RefreshFunctionVin,
    ) -> None:
        self.update_driving_range = self._debounce(hass, vin, update_driving_range)
        self.update_charging = self._debounce(hass, vin, update_charging)
        self.update_air_conditioning = self._debounce(
            hass, vin, update_air_conditioning
        )
        self.update_vehicle = self._debounce(hass, vin, update_vehicle)

    def _debounce(
        self, hass: HomeAssistant, vin: str, func: RefreshFunctionVin
    ) -> RefreshFunction:
        return MySkodaDebouncer(hass, vin, func).async_call


class MySkodaDataUpdateCoordinator(DataUpdateCoordinator[State]):
    """See `DataUpdateCoordinator`.

    This class manages all data from the MySkoda API.
    """

    myskoda: MySkoda
    config: ConfigEntry
    data: State
    refresh: dict[str, DebouncedRefresh]

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Create a new coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=FETCH_INTERVAL_IN_MINUTES),
            always_update=False,
        )
        self.myskoda = MySkoda(async_get_clientsession(hass))
        self.config = config
        self.refresh = {}

    async def async_login(self) -> bool:
        """Login to the MySkoda API. Will return `True` if successful."""

        try:
            await self.myskoda.connect(
                self.config.data["email"],
                self.config.data["password"],
                get_default_context(),
            )
            self.myskoda.subscribe(self._on_mqtt_event)
            vehicles = await self.myskoda.list_vehicle_vins()
        except Exception:
            _LOGGER.error("Login with MySkoda failed.")
            return False

        for vin in vehicles:
            self.refresh[vin] = DebouncedRefresh(
                self.hass,
                vin,
                update_air_conditioning=self._update_air_conditioning,
                update_vehicle=self._update_vehicle,
                update_charging=self._update_charging,
                update_driving_range=self._update_driving_range,
            )

        return True

    async def _async_update_data(self) -> State:
        vehicles = await self.myskoda.get_all_vehicles()
        user = await self.myskoda.get_user()
        return State(vehicles, user)

    async def _on_mqtt_event(self, event: Event) -> None:
        if event.type == EventType.OPERATION:
            await self._on_operation_event(event)
        if event.type == EventType.SERVICE_EVENT:
            if event.topic == ServiceEventTopic.CHARGING:
                await self._on_charging_event(event)
            if event.topic == ServiceEventTopic.ACCESS:
                await self._on_access_event(event)
            if event.topic == ServiceEventTopic.AIR_CONDITIONING:
                await self._on_air_conditioning_event(event)

    async def _on_operation_event(self, event: EventOperation) -> None:
        if event.operation.status == OperationStatus.IN_PROGRESS:
            return
        if event.operation.operation in [
            OperationName.STOP_AIR_CONDITIONING,
            OperationName.START_AIR_CONDITIONING,
            OperationName.SET_AIR_CONDITIONING_TARGET_TEMPERATURE,
            OperationName.START_WINDOW_HEATING,
            OperationName.STOP_WINDOW_HEATING,
        ]:
            await self.refresh[event.vin].update_air_conditioning()
        if event.operation.operation in [
            OperationName.UPDATE_CHARGE_LIMIT,
            OperationName.UPDATE_CARE_MODE,
            OperationName.UPDATE_CHARGING_CURRENT,
            OperationName.START_CHARGING,
            OperationName.STOP_CHARGING,
        ]:
            await self.refresh[event.vin].update_charging()

    async def _on_charging_event(self, event: EventCharging):
        vehicle = self.data.vehicles[event.vin]

        data = event.event.data

        if vehicle.charging is None or vehicle.charging.status is None:
            await self.refresh[event.vin].update_charging()
        else:
            status = vehicle.charging.status

            status.battery.remaining_cruising_range_in_meters = data.charged_range
            status.battery.state_of_charge_in_percent = data.soc
            status.state = data.state
            status.state = data.state
        self.async_set_updated_data

        if vehicle.driving_range is None:
            await self.refresh[event.vin].update_driving_range()
        else:
            vehicle.driving_range.primary_engine_range.current_so_c_in_percent = (
                data.soc
            )
            vehicle.driving_range.primary_engine_range.remaining_range_in_km = (
                data.charged_range
            )

        self.set_updated_vehicle(vehicle)

    async def _on_access_event(self, event: EventAccess):
        await self.refresh[event.vin].update_vehicle()

    async def _on_air_conditioning_event(self, event: EventAirConditioning):
        await self.refresh[event.vin].update_air_conditioning()

    def _unsub_refresh(self):
        return

    def set_updated_vehicle(self, vehicle: Vehicle) -> None:
        self.data.vehicles[vehicle.info.vin] = vehicle
        self.async_set_updated_data(self.data)

    async def _update_driving_range(self, vin: str) -> None:
        _LOGGER.debug("Updating driving range for %s", vin)
        driving_range = await self.myskoda.get_driving_range(vin)
        vehicle = self.data.vehicles[vin]
        vehicle.driving_range = driving_range
        self.set_updated_vehicle(vehicle)

    async def _update_charging(self, vin: str) -> None:
        _LOGGER.debug("Updating charging information for %s", vin)
        charging = await self.myskoda.get_charging(vin)
        vehicle = self.data.vehicles[vin]
        vehicle.charging = charging
        self.set_updated_vehicle(vehicle)

    async def _update_air_conditioning(self, vin: str) -> None:
        _LOGGER.debug("Updating air conditioning for %s", vin)
        air_conditioning = await self.myskoda.get_air_conditioning(vin)
        vehicle = self.data.vehicles[vin]
        vehicle.air_conditioning = air_conditioning
        self.set_updated_vehicle(vehicle)

    async def _update_vehicle(self, vin: str) -> None:
        _LOGGER.debug("Updating full vehicle for %s", vin)
        vehicle = await self.myskoda.get_vehicle(vin)
        self.set_updated_vehicle(vehicle)
