"""Config flow for JFL Alarm integration."""
from __future__ import annotations

import logging
import socket
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_KEEP_ALIVE_INTERVAL,
    CONF_ENABLE_KEEP_ALIVE,
    CONF_GET_STATE_INTERVAL,
    CONF_ENABLE_GET_STATE,
    DEFAULT_PORT,
    DEFAULT_KEEP_ALIVE_INTERVAL,
    DEFAULT_GET_STATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default="JFL Alarm"): str,
    }
)

STEP_OPTIONS_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_KEEP_ALIVE_INTERVAL, default=DEFAULT_KEEP_ALIVE_INTERVAL
        ): vol.All(int, vol.Range(min=5000, max=300000)),
        vol.Optional(CONF_ENABLE_KEEP_ALIVE, default=True): bool,
        vol.Optional(
            CONF_GET_STATE_INTERVAL, default=DEFAULT_GET_STATE_INTERVAL
        ): vol.All(int, vol.Range(min=1000, max=60000)),
        vol.Optional(CONF_ENABLE_GET_STATE, default=True): bool,
    }
)


class JFLAlarmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for JFL Alarm."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Validate the host and port
            try:
                await self._test_connection(user_input[CONF_HOST], user_input[CONF_PORT])
                
                # Check if already configured
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}_{user_input[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()
                
                self._user_data = user_input
                return await self.async_step_options()
                
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
        
        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA, 
            errors=errors
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the options step."""
        if user_input is not None:
            # Combine user data with options
            config_data = {**self._user_data, **user_input}
            
            return self.async_create_entry(
                title=config_data[CONF_NAME],
                data=config_data,
            )
        
        return self.async_show_form(
            step_id="options",
            data_schema=STEP_OPTIONS_DATA_SCHEMA,
        )

    async def _test_connection(self, host: str, port: int) -> None:
        """Test if we can connect to the host."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result != 0:
                raise CannotConnect("Cannot connect to host")
                
        except socket.error as err:
            raise CannotConnect(f"Socket error: {err}") from err

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> JFLAlarmOptionsFlowHandler:
        """Create the options flow."""
        return JFLAlarmOptionsFlowHandler(config_entry)


class JFLAlarmOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle JFL Alarm options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values
        current_keep_alive_interval = self.config_entry.data.get(
            CONF_KEEP_ALIVE_INTERVAL, DEFAULT_KEEP_ALIVE_INTERVAL
        )
        current_enable_keep_alive = self.config_entry.data.get(
            CONF_ENABLE_KEEP_ALIVE, True
        )
        current_get_state_interval = self.config_entry.data.get(
            CONF_GET_STATE_INTERVAL, DEFAULT_GET_STATE_INTERVAL
        )
        current_enable_get_state = self.config_entry.data.get(
            CONF_ENABLE_GET_STATE, True
        )

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_KEEP_ALIVE_INTERVAL, default=current_keep_alive_interval
                ): vol.All(int, vol.Range(min=5000, max=300000)),
                vol.Optional(
                    CONF_ENABLE_KEEP_ALIVE, default=current_enable_keep_alive
                ): bool,
                vol.Optional(
                    CONF_GET_STATE_INTERVAL, default=current_get_state_interval
                ): vol.All(int, vol.Range(min=1000, max=60000)),
                vol.Optional(
                    CONF_ENABLE_GET_STATE, default=current_enable_get_state
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
