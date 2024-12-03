"""Config flow for the MySkoda integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow as BaseConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    callback,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaFlowError,
    SchemaFlowFormStep,
    SchemaOptionsFlowHandler,
)
from homeassistant.util.ssl import get_default_context
from myskoda import MySkoda

from .const import (
    DOMAIN,
    CONF_POLL_INTERVAL,
    CONF_POLL_INTERVAL_MIN,
    CONF_POLL_INTERVAL_MAX,
    CONF_SPIN,
    CONF_READONLY,
)

_LOGGER = logging.getLogger(__name__)


async def validate_options_input(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    """Validate options are valid."""

    if CONF_POLL_INTERVAL in user_input:
        polling_interval: int = user_input[CONF_POLL_INTERVAL]
        if not CONF_POLL_INTERVAL_MIN <= polling_interval <= CONF_POLL_INTERVAL_MAX:
            raise SchemaFlowError("invalid_polling_interval")

    if CONF_SPIN in user_input:
        s_pin: str = user_input[CONF_SPIN]
        if not s_pin.isdigit():
            raise SchemaFlowError("invalid_spin_format")

    return user_input


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Check that the inputs are valid."""
    hub = MySkoda(
        async_get_clientsession(hass), get_default_context(), mqtt_enabled=False
    )

    await hub.connect(data["email"], data["password"])
    await hub.disconnect()


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("email"): str,
        vol.Required("password"): str,
    }
)
OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required("tracing", default=False): bool,
        vol.Optional(CONF_POLL_INTERVAL): int,
        vol.Optional(CONF_READONLY, default=False): bool,
        vol.Optional(CONF_SPIN): str,
    }
)
OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(
        OPTIONS_SCHEMA,
        validate_user_input=validate_options_input,
    )
}


class ConfigFlow(BaseConfigFlow, domain=DOMAIN):
    """Handle a config flow for MySkoda."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=user_input["email"], data=user_input)

        # Only called if there was an error.
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return SchemaOptionsFlowHandler(config_entry, OPTIONS_FLOW)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
