from aiohttp import ClientSession
from random import choices
import string
import hashlib
import base64
from .authorization import IDKSession, idk_authorize
import logging

_LOGGER = logging.getLogger(__name__)

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