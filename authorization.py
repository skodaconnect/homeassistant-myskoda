from datetime import datetime, timedelta
from typing import Dict
from aiohttp import ClientSession, FormData
import logging
from bs4 import BeautifulSoup
import re
import jwt
import yaml
import json
import hashlib
import base64
import string
import random
import uuid
from typing import cast

from homeassistant.exceptions import HomeAssistantError

from .const import CLIENT_ID, BASE_URL_SKODA, BASE_URL_IDENT

_LOGGER = logging.getLogger(__name__)


class IDKCredentials:
    hmac: str
    csrf: str
    relay_state: str
    email: str
    password: str

    def __init__(self, dict: Dict, email: str, password: str):
        self.email = email
        self.password = password
        self.update(dict)

    def update(self, dict: Dict):
        self.csrf = cast(str, dict.get("csrf_token"))
        self.hmac = cast(str, dict.get("templateModel", {}).get("hmac"))
        self.relay_state = dict.get("templateModel", {}).get("relayState")


class IDKAuthorizationCodes:
    code: str
    token_type: str
    id_token: str

    def __init__(self, dict):
        self.code = dict.get("code")
        self.token_type = dict.get("token_type")
        self.id_token = dict.get("id_token")
        self.relay_state = dict.get("templateModel", {}).get("relayState")


class IDKSession:
    access_token: str
    refresh_token: str
    id_token: str

    def __init__(self, dict):
        self.access_token = dict.get("accessToken")
        self.refresh_token = dict.get("refreshToken")
        self.id_token = dict.get("idToken")

    async def perform_refresh(self, session: ClientSession):
        json_data = {
            "token": self.refresh_token
        }
        async with session.post(
            f"{BASE_URL_SKODA}/api/v1/authentication/refresh-token?tokenType=CONNECT",
            json=json_data
        ) as response:
            dict = json.loads(await response.text())
            self.access_token = dict.get("accessToken")
            self.refresh_token = dict.get("refreshToken")
            self.id_token = dict.get("idToken")

    async def get_access_token(self, session: ClientSession) -> str:
        meta = jwt.decode(self.access_token, options={"verify_signature": False})
        expiry = datetime.fromtimestamp(cast(float, meta.get("exp")))
        if datetime.now() + timedelta(minutes=10) > expiry:
            _LOGGER.info("Refreshing IDK access token")
            await self.perform_refresh(session)
        return self.access_token

def _extract_states_from_website(html) -> Dict[str, str]:
    """
    Information such as the CSRF or the hmac will be available in the HTML.

    This method will parse the information from a `<script>` tag in the HTML using BS4.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Regex to extract the information assigned to `window._IDK` from the script tag.
    json_object = re.compile(r"window\._IDK\s=\s((?:\n|.)*?)$")

    dict = None

    # Search through all script tags and find the first one to match the Regex.
    for script in soup.find_all("script"):
        if len(script.contents) != 1:
            continue
        content = script.contents[0].strip()
        result = json_object.search(content)
        if result == None:
            continue

        result = result.group(1)
        # Load the info using YAML, since the syntax used in the script is YAML compatible,
        # but not JSON compatible (missing quotes around field names, trailing commas).
        dict = yaml.safe_load(result)

    if dict == None:
        raise InternalAuthorizationError

    return dict


async def _initial_oidc_authorize(
    session: ClientSession, verifier: str, email: str, password: str
) -> IDKCredentials:
    """
    First step of the login process.

    This calls the route for initial authorization, which will contain the initial SSO information
    such as the CSRF or the HMAC.
    """

    # A SHA256 hash of the random "verifier" string will be transmitted as a challenge.
    # This is part of the OAUTH2 PKCE process. It is described here in detail: https://www.oauth.com/oauth2-servers/pkce/authorization-request/
    verifier_hash = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = (
        base64.b64encode(verifier_hash)
        .decode("utf-8")
        .replace("+", "-")
        .replace("/", "_")
        .rstrip("=")
    )

    params = {
        "client_id": CLIENT_ID,
        "nonce": str(uuid.uuid4()),
        "redirect_uri": "myskoda://redirect/login/",
        "response_type": "code id_token",
        # OpenID scopes. Can be found here: https://identity.vwgroup.io/.well-known/openid-configuration
        "scope": "address badge birthdate cars driversLicense dealers email mileage mbb nationalIdentifier openid phone profession profile vin",
        "code_challenge": challenge,
        "code_challenge_method": "s256",
        "prompt": "login",
    }
    async with session.get(
        f"{BASE_URL_IDENT}/oidc/v1/authorize", params=params
    ) as response:
        dict = _extract_states_from_website(await response.text())
        return IDKCredentials(dict, email, password)


async def _enter_email_address(
    session: ClientSession, login_meta: IDKCredentials
) -> IDKCredentials:
    """
    Second step in the login process.

    Will post only the email address to the backend. The password will follow in a later request.
    """
    form_data = FormData()
    form_data.add_field("relayState", login_meta.relay_state)
    form_data.add_field("email", login_meta.email)
    form_data.add_field("hmac", login_meta.hmac)
    form_data.add_field("_csrf", login_meta.csrf)

    async with session.post(
        f"{BASE_URL_IDENT}/signin-service/v1/{CLIENT_ID}/login/identifier",
        data=form_data(),
    ) as response:
        dict = _extract_states_from_website(await response.text())
        login_meta.update(dict)
        return login_meta


async def _enter_password(
    session: ClientSession, login_meta: IDKCredentials
) -> IDKAuthorizationCodes:
    """
    Third step in the login process.

    Post both the email address and the password to the backend.
    This will return a token which can then be used in the skoda services to authenticate.
    """
    form_data = FormData()
    form_data.add_field("relayState", login_meta.relay_state)
    form_data.add_field("email", login_meta.email)
    form_data.add_field("password", login_meta.password)
    form_data.add_field("hmac", login_meta.hmac)
    form_data.add_field("_csrf", login_meta.csrf)

    # The following is a bit hacky:
    # The backend will redirect multiple times after the login was successful.
    # The last redirect will redirect back to the `MySkoda` app in Android, using the `myskoda://` URL prefix.
    # The following loop will follow all redirects until the last redirect to `myskoda://` is encountered.
    # This last URL will contain the token.
    async with session.post(
        f"{BASE_URL_IDENT}/signin-service/v1/{CLIENT_ID}/login/authenticate",
        data=form_data(),
        allow_redirects=False,
    ) as response:
        location = response.headers["Location"]
        while not location.startswith("myskoda://"):
            async with session.get(location, allow_redirects=False) as response:
                location = response.headers["Location"]
        codes = location.replace("myskoda://redirect/login/#", "")

        # The last redirection starting with `myskoda://` was encountered.
        # The URL will contain the information we need as query parameters, without the leading `?`.
        dict = {}
        for code in codes.split("&"):
            [key, value] = code.split("=")
            dict[key] = value

        return IDKAuthorizationCodes(dict)


async def _exchange_auth_code_for_idk_session(
    session: ClientSession, code: str, verifier: str
) -> IDKSession:
    """
    Exchange the ident login code for an auth token from Skoda.

    This will return multiple tokens, such as an access token and a refresh token.
    """
    json_data = {
        "code": code,
        "redirectUri": "myskoda://redirect/login/",
        "verifier": verifier,
    }

    async with session.post(
        f"{BASE_URL_SKODA}/api/v1/authentication/exchange-authorization-code?tokenType=CONNECT",
        json=json_data,
        allow_redirects=False,
    ) as response:
        login_data = json.loads(await response.text())
        return IDKSession(login_data)


async def idk_authorize(
    session: ClientSession, email: str, password: str
) -> IDKSession:
    """
    Perform the full login process.

    Must be called before any other methods on the class can be called.
    """

    # Generate a random string for the OAUTH2 PKCE challenge. (https://www.oauth.com/oauth2-servers/pkce/authorization-request/)
    verifier = "".join(random.choices(string.ascii_uppercase + string.digits, k=16))

    # Call the initial OIDC (OpenID Connect) authorization, giving us the initial SSO information.
    # The full flow is explain a little bit here: https://openid.net/specs/openid-connect-core-1_0.html#ImplicitFlowAuth
    login_meta = await _initial_oidc_authorize(session, verifier, email, password)

    # Use the information to login with the email address, which is an extra step before the actual login.
    login_meta = await _enter_email_address(session, login_meta)

    # Perform the actual login which will result in a token that can be exchanged for an access token at the Skoda server.
    authentication = await _enter_password(session, login_meta)

    # Exchange the token for access and refresh tokens (JWT format).
    idk_session = await _exchange_auth_code_for_idk_session(
        session, authentication.code, verifier
    )

    return idk_session


class InternalAuthorizationError(HomeAssistantError):
    """Error to indicate that something unexpected happened during authorization."""
