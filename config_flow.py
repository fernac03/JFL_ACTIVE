# config_flow.py
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
import logging
import socket
from .const import (
    DOMAIN,
    CONF_ALT_NIGHT_MODE,
    CONF_AUTO_BYPASS,
    CONF_CODE_ARM_REQUIRED,
    CONF_CODE_REQUIRED,
    DEFAULT_ARM_OPTIONS,
    DEFAULT_DEVICE_HOST,
    DEFAULT_DEVICE_PORT,
    OPTIONS_ARM
)

EDIT_KEY = "edit_selection"
EDIT_SETTINGS = "Arming Settings"

_LOGGER = logging.getLogger(__name__)
class AlarmIntegrationFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2
    def __init__(self):
        """Initialize JFL Active ConfigFlow."""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry,) -> AlarmIntegrationOptionsFlowHandler:
        """Get the options flow for JFL Active."""
        return AlarmIntegrationOptionsFlowHandler(config_entry)
    
    async def async_step_user(self, user_input=None):
        """Handle JFL Active  setup."""
        errors = {}
        if user_input is not None:
            if _device_already_added(
                self._async_current_entries(), user_input
            ):
                return self.async_abort(reason="already_configured")
            connection = {}
            host = connection[CONF_HOST] = user_input[CONF_HOST]
            port = connection[CONF_PORT] = user_input[CONF_PORT]
            title = f"{host}:{port}"
            device = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            try:
                device.bind((host,port))
                device.listen()
                device.shutdown(2)
                _LOGGER.info("Connection from JFL Active possible")
                return self.async_create_entry(
                    title=title, data={**connection}
                )
            except OSError as err:
                _LOGGER.debug("error:%s",err)
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during JFL Active setup")
                errors["base"] = "unknown"

        schema = vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_DEVICE_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_DEVICE_PORT): int,
                }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

class AlarmIntegrationOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle JFL Active options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize JFL options flow."""
        self.arm_options = config_entry.options.get(OPTIONS_ARM, DEFAULT_ARM_OPTIONS)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            if user_input[EDIT_KEY] == EDIT_SETTINGS:
                return await self.async_step_arm_settings()
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(EDIT_KEY, default=EDIT_SETTINGS): vol.In(
                        [EDIT_SETTINGS]
                    )
                },
            ),
        )

    async def async_step_arm_settings(self, user_input=None):
        """Arming options form."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={OPTIONS_ARM: user_input},
            )

        return self.async_show_form(
            step_id="arm_settings",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ALT_NIGHT_MODE,
                        default=self.arm_options[CONF_ALT_NIGHT_MODE],
                    ): bool,
                    vol.Optional(
                        CONF_AUTO_BYPASS, default=self.arm_options[CONF_AUTO_BYPASS]
                    ): bool,
                    vol.Optional(
                        CONF_CODE_ARM_REQUIRED,
                        default=self.arm_options[CONF_CODE_ARM_REQUIRED],
                    ): bool,
                    vol.Required(
                        CONF_CODE_REQUIRED,
                        default=self.arm_options[CONF_CODE_REQUIRED],
                    ): str,
                },
            ),
        )
def _device_already_added(current_entries, user_input):
    """Determine if entry has already been added to HA."""
    user_host = user_input.get(CONF_HOST)
    user_port = user_input.get(CONF_PORT)

    for entry in current_entries:
        entry_host = entry.data.get(CONF_HOST)
        entry_port = entry.data.get(CONF_PORT)

        if (
            user_host == entry_host
            and user_port == entry_port
        ):
            return True

    return False
