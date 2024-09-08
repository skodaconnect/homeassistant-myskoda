from aiohttp import ClientSession
from .authorization import IDKSession, idk_authorize
import logging
from .const import BASE_URL_SKODA

_LOGGER = logging.getLogger(__name__)

class Vehicle:
    battery_capacity_kwh: int
    engine_power_kw: int
    engine_type: str
    model: str
    model_year: str
    title: str
    vin: str
    software_version: str

    def __init__(self, dict):
        dict = dict.get("deliveredVehicle")
        self.vin = dict.get("vin")
        self.software_version = dict.get("softwareVersion")

        dict = dict.get("specification")
        self.battery_capacity_kwh = dict.get("battery", {}).get("capacityInKWh")
        self.engine_power_kw = dict.get("engine", {}).get("powerInKW")
        self.engine_type = dict.get("engine", {}).get("type")
        self.model = dict.get("model")
        self.model_year = dict.get("modelYear")
        self.title = dict.get("title")

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

    async def get_vehicle(self):
        async with self.session.get(f"{BASE_URL_SKODA}/api/v2/garage/initial-vehicle?connectivityGenerations=MOD3&connectivityGenerations=MOD4", headers=self._headers()) as response:
            return Vehicle(await response.json())

    def _headers(self):
        return {
            "authorization": f"Bearer {self.idk_session.access_token}"
        }
