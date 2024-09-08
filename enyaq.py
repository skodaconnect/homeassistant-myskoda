from asyncio import gather
from datetime import datetime
from aiohttp import ClientSession
from .authorization import IDKSession, idk_authorize
import logging
from .const import BASE_URL_SKODA

_LOGGER = logging.getLogger(__name__)


class Info:
    battery_capacity_kwh: int
    engine_power_kw: int
    engine_type: str
    model: str
    model_id: str
    model_year: str
    title: str
    vin: str
    software_version: str

    def __init__(self, dict):
        self.vin = dict.get("vin")
        self.software_version = dict.get("softwareVersion")

        dict = dict.get("specification")
        self.battery_capacity_kwh = dict.get("battery", {}).get("capacityInKWh")
        self.engine_power_kw = dict.get("engine", {}).get("powerInKW")
        self.engine_type = dict.get("engine", {}).get("type")
        self.model = dict.get("model")
        self.model_year = dict.get("modelYear")
        self.model_id = dict.get("systemModelId")
        self.title = dict.get("title")


class Charging:
    remaining_distance_m: int
    battery_percent: int
    charging_care_mode: bool
    charging_power_kw: float
    charge_type: str
    charging_rate_in_km_h: float
    remaining_time_min: str
    state: str
    target_percent: int
    use_reduced_current: bool

    def __init__(self, dict):
        self.target_percent = dict.get("settings", {}).get(
            "targetStateOfChargeInPercent"
        )
        self.charging_care_mode = dict.get("settings", {}).get("chargingCareMode") == "ACTIVATED"
        self.use_reduced_current = dict.get("settings", {}).get("maxChargeCurrentAc") == "REDUCED"

        dict = dict.get("status")
        self.remaining_distance_m = dict.get("battery", {}).get(
            "remainingCruisingRangeInMeters"
        )
        self.battery_percent = dict.get("battery", {}).get("stateOfChargeInPercent")
        self.charging_power_kw = dict.get("chargePowerInKw")

        # "AC"
        self.charge_type = dict.get("chargeType")

        self.charging_rate_in_km_h = dict.get("chargingRateInKilometersPerHour")
        self.remaining_time_min = dict.get("remainingTimeToFullyChargedInMinutes")

        # "CONNECT_CABLE": Not connected
        # "READY_FOR_CHARGING": Connected, but full
        # "CONSERVING": Connected, but full
        # "CHARGING": Connected and charging
        self.state = dict.get("state")

class Status:
    doors_open: bool
    bonnet_open: bool
    trunk_open: bool
    doors_locked: bool
    lights_on: bool
    locked: bool
    windows_open: bool
    car_captured: datetime

    def __init__(self, dict):
        self.bonnet_open = dict.get("detail", {}).get("bonnet") == "OPEN"
        self.doors_open = dict.get("overall", {}).get("doors") == "OPEN"
        self.trunk_open = dict.get("detail", {}).get("trunk") == "OPEN"
        self.doors_locked = dict.get("overall", {}).get("doorsLocked") == "YES"
        self.lights_on = dict.get("overall", {}).get("lights") == "ON"
        self.locked = dict.get("overall", {}).get("locked") == "YES"
        self.windows_open = dict.get("overall", {}).get("windows") == "OPEN"
        self.car_captured = datetime.fromisoformat(dict.get("carCapturedTimestamp"))


class AirConditioning:
    window_heating_enabled: bool
    window_heating_front_on: bool
    window_heating_rear_on: bool
    target_temperature_celsius: float
    steering_wheel_position: str
    air_conditioning_on: bool
    state: bool
    charger_connected: bool
    charger_locked: bool
    time_to_reach_target_temperature: str

    def __init__(self, dict):
        self.window_heating_enabled = dict.get("windowHeatingEnabled")
        self.window_heating_front_on = (
            dict.get("windowHeatingState", {}).get("front") == "ON"
        )
        self.window_heating_rear_on = (
            dict.get("windowHeatingState", {}).get("rear") == "ON"
        )
        self.target_temperature_celsius = dict.get("targetTemperature", {}).get(
            "temperatureValue"
        )
        self.steering_wheel_position = dict.get("steeringWheelPosition")
        self.air_conditioning_on = (
            dict.get("state") == "ON"
            or dict.get("state") == "COOLING"
            or dict.get("state") == "HEATING"
        )
        # COOLING, HEATING, OFF, ON
        self.state = dict.get("state")

        self.charger_connected = dict.get("chargerConnectionState") == "CONNECTED"
        self.charger_locked = dict.get("chargerLockState") == "LOCKED"
        self.time_to_reach_target_temperature = dict.get(
            "estimatedDateTimeToReachTargetTemperature"
        )


class Position:
    city: str
    country: str
    country_code: str
    house_number: str
    street: str
    zip_code: str
    lat: float
    lng: float

    def __init__(self, dict):
        dict = dict.get("positions")[0]
        self.city = dict.get("address", {}).get("city")
        self.country = dict.get("address", {}).get("country")
        self.country_code = dict.get("address", {}).get("countryCode")
        self.house_number = dict.get("address", {}).get("houseNumber")
        self.street = dict.get("address", {}).get("street")
        self.zip_code = dict.get("address", {}).get("zipCode")
        self.lat = dict.get("gpsCoordinates", {}).get("latitude")
        self.lng = dict.get("gpsCoordinates", {}).get("longitude")


class Health:
    mileage_km: int

    def __init__(self, dict):
        self.mileage_km = dict.get("mileageInKm")


class Vehicle:
    info: Info
    charging: Charging
    status: Status
    air_conditioning: AirConditioning
    position: Position
    health: Health

    def __init__(
        self,
        info: Info,
        charging: Charging,
        status: Status,
        air_conditioning: AirConditioning,
        position: Position,
        health: Health,
    ):
        self.info = info
        self.charging = charging
        self.status = status
        self.air_conditioning = air_conditioning
        self.position = position
        self.health = health


class EnyaqHub:
    session: ClientSession
    idk_session: IDKSession

    def __init__(self, session: ClientSession) -> None:
        self.session = session

    async def authenticate(self, email: str, password: str) -> bool:
        """
        Perform the full login process.

        Must be called before any other methods on the class can be called.
        """

        self.idk_session = await idk_authorize(self.session, email, password)

        _LOGGER.info("IDK Authorization was successful.")

        return True

    async def get_info(self, vin):
        async with self.session.get(
            f"{BASE_URL_SKODA}/api/v2/garage/vehicles/{vin}", headers=self._headers()
        ) as response:
            _LOGGER.info(f"Received info for vin {vin}")
            return Info(await response.json())

    async def get_charging(self, vin):
        async with self.session.get(
            f"{BASE_URL_SKODA}/api/v1/charging/{vin}", headers=self._headers()
        ) as response:
            _LOGGER.info(f"Received charging for vin {vin}")
            return Charging(await response.json())

    async def get_status(self, vin):
        async with self.session.get(
            f"{BASE_URL_SKODA}/api/v2/vehicle-status/{vin}", headers=self._headers()
        ) as response:
            _LOGGER.info(f"Received status for vin {vin}")
            return Status(await response.json())

    async def get_air_conditioning(self, vin):
        async with self.session.get(
            f"{BASE_URL_SKODA}/api/v2/air-conditioning/{vin}", headers=self._headers()
        ) as response:
            _LOGGER.info(f"Received air conditioning for vin {vin}")
            return AirConditioning(await response.json())

    async def get_position(self, vin):
        async with self.session.get(
            f"{BASE_URL_SKODA}/api/v1/maps/positions?vin={vin}", headers=self._headers()
        ) as response:
            _LOGGER.info(f"Received position for vin {vin}")
            return Position(await response.json())

    async def get_health(self, vin):
        async with self.session.get(
            f"{BASE_URL_SKODA}/api/v1/vehicle-health-report/warning-lights/{vin}",
            headers=self._headers(),
        ) as response:
            _LOGGER.info(f"Received health for vin {vin}")
            return Health(await response.json())

    async def list_vehicles(self):
        async with self.session.get(
            f"{BASE_URL_SKODA}/api/v2/garage", headers=self._headers()
        ) as response:
            json = await response.json()
            vehicles = []
            for vehicle in json["vehicles"]:
                vehicles.append(vehicle["vin"])
            return vehicles

    async def get_vehicle(self, vin) -> Vehicle:
        [info, charging, status, air_conditioning, position, health] = await gather(
            *[
                self.get_info(vin),
                self.get_charging(vin),
                self.get_status(vin),
                self.get_air_conditioning(vin),
                self.get_position(vin),
                self.get_health(vin),
            ]
        )
        return Vehicle(
            info=info,
            charging=charging,
            status=status,
            air_conditioning=air_conditioning,
            position=position,
            health=health,
        )

    async def get_all_vehicles(self) -> list[Vehicle]:
        return await gather(
            *[self.get_vehicle(vehicle) for vehicle in await self.list_vehicles()]
        )

    def _headers(self):
        return {"authorization": f"Bearer {self.idk_session.access_token}"}

    async def stop_air_conditioning(self, vin):
        async with self.session.post(
            f"{BASE_URL_SKODA}/api/v2/air-conditioning/{vin}/stop",
            headers=self._headers(),
        ) as response:
            await response.text()

    async def start_air_conditioning(self, vin, temperature):
        json_data = {
            "heaterSource": "ELECTRIC",
            "targetTemperature": {
                "temperatureValue": temperature,
                "unitInCar": "CELSIUS",
            },
        }
        async with self.session.post(
            f"{BASE_URL_SKODA}/api/v2/air-conditioning/{vin}/start",
            headers=self._headers(),
            json=json_data,
        ) as response:
            await response.text()

    async def set_target_temperature(self, vin, temperature):
        json_data = {"temperatureValue": temperature, "unitInCar": "CELSIUS"}
        async with self.session.post(
            f"{BASE_URL_SKODA}/api/v2/air-conditioning/{vin}/settings/target-temperature",
            headers=self._headers(),
            json=json_data,
        ) as response:
            await response.text()

    async def start_window_heating(self, vin):
        async with self.session.post(
            f"{BASE_URL_SKODA}/api/v2/air-conditioning/{vin}/start-window-heating",
            headers=self._headers(),
        ) as response:
            await response.text()

    async def stop_window_heating(self, vin):
        async with self.session.post(
            f"{BASE_URL_SKODA}/api/v2/air-conditioning/{vin}/stop-window-heating",
            headers=self._headers(),
        ) as response:
            await response.text()

    async def set_charge_limit(self, vin, limit: int):
        json_data = {
            "targetSOCInPercent": limit
        }
        async with self.session.put(
            f"{BASE_URL_SKODA}/api/v1/charging/{vin}/set-charge-limit",
            headers=self._headers(),
            json=json_data
        ) as response:
            await response.text()

    async def set_battery_care_mode(self, vin, enabled: bool):
        json_data = {
            "chargingCareMode": "ACTIVATED" if enabled else "DEACTIVATED"
        }
        async with self.session.put(
            f"{BASE_URL_SKODA}/api/v1/charging/{vin}/set-care-mode",
            headers=self._headers(),
            json=json_data
        ) as response:
            await response.text()

    async def set_reduced_current_limit(self, vin, reduced: bool):
        json_data = {
            "chargingCurrent": "REDUCED" if reduced else "MAXIMUM"
        }
        async with self.session.put(
            f"{BASE_URL_SKODA}/api/v1/charging/{vin}/set-charging-current",
            headers=self._headers(),
            json=json_data
        ) as response:
            await response.text()