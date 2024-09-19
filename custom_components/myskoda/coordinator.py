from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.ssl import get_default_context
from myskoda import MySkoda, Vehicle
from myskoda.event import Event, EventAccess, EventAirConditioning, ServiceEventTopic
from myskoda.models.user import User
from myskoda.mqtt import EventCharging, EventType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class State:
    vehicles: dict[str, Vehicle]
    user: User

    def __init__(self, vehicles: list[Vehicle], user: User) -> None:
        self.vehicles = {}
        for vehicle in vehicles:
            self.vehicles[vehicle.info.vin] = vehicle
        self.user = user


class MySkodaDataUpdateCoordinator(DataUpdateCoordinator[State]):
    """See `DataUpdateCoordinator`.

    This class manages all data from the MySkoda API.
    """

    myskoda: MySkoda
    config: ConfigEntry
    data: State

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Create a new coordinator."""

        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=30)
        )
        self.myskoda = MySkoda(async_get_clientsession(hass))
        self.config = config

    async def async_login(self) -> bool:
        """Login to the MySkoda API. Will return `True` if successful."""

        try:
            await self.myskoda.connect(
                self.config.data["email"],
                self.config.data["password"],
                get_default_context(),
            )
            self.myskoda.subscribe(self._on_mqtt_event)
            return True
        except Exception:
            _LOGGER.error("Login with MySkoda failed.")
            return False

    async def _async_update_data(self) -> State:
        vehicles = await self.myskoda.get_all_vehicles()
        user = await self.myskoda.get_user()
        return State(vehicles, user)

    async def _on_mqtt_event(self, event: Event) -> None:
        if event.type != EventType.SERVICE_EVENT:
            return
        if event.topic == ServiceEventTopic.CHARGING:
            await self._on_charging_event(event)
        if event.topic == ServiceEventTopic.ACCESS:
            await self._on_access_event(event)
        if event.topic == ServiceEventTopic.AIR_CONDITIONING:
            await self._on_air_conditioning_event(event)

    async def _on_charging_event(self, event: EventCharging):
        vehicle = self.data.vehicles[event.vin]

        data = event.event.data

        if vehicle.charging is None or vehicle.charging.status is None:
            await self.update_charging(event.vin)
        else:
            status = vehicle.charging.status

            status.battery.remaining_cruising_range_in_meters = data.charged_range
            status.battery.state_of_charge_in_percent = data.soc
            status.state = data.state
            status.state = data.state

        if vehicle.driving_range is None:
            await self.update_driving_range(event.vin)
        else:
            vehicle.driving_range.primary_engine_range.current_so_c_in_percent = (
                data.soc
            )
            vehicle.driving_range.primary_engine_range.remaining_range_in_km = (
                data.charged_range
            )

        self._set_updated_vehicle(vehicle)

    async def _on_access_event(self, event: EventAccess):
        await self.update_vehicle(event.vin)

    async def _on_air_conditioning_event(self, event: EventAirConditioning):
        await self.update_air_conditioning(event.vin)

    def _unsub_refresh(self):
        return

    def _set_updated_vehicle(self, vehicle: Vehicle) -> None:
        self.data.vehicles[vehicle.info.vin] = vehicle
        self.async_set_updated_data(self.data)

    async def update_driving_range(self, vin: str) -> None:
        driving_range = await self.myskoda.get_driving_range(vin)
        vehicle = self.data.vehicles[vin]
        vehicle.driving_range = driving_range
        self._set_updated_vehicle(vehicle)

    async def update_charging(self, vin: str) -> None:
        charging = await self.myskoda.get_charging(vin)
        vehicle = self.data.vehicles[vin]
        vehicle.charging = charging
        self._set_updated_vehicle(vehicle)

    async def update_air_conditioning(self, vin: str) -> None:
        air_conditioning = await self.myskoda.get_air_conditioning(vin)
        vehicle = self.data.vehicles[vin]
        vehicle.air_conditioning = air_conditioning
        self._set_updated_vehicle(vehicle)

    async def update_vehicle(self, vin: str) -> None:
        vehicle = await self.myskoda.get_vehicle(vin)
        self._set_updated_vehicle(vehicle)
