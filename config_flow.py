"""Config flow for JFL Active20."""
from __future__ import annotations

import logging
import socket

from adext import AdExt
from alarmdecoder.util import NoDeviceError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA as BINARY_SENSOR_DEVICE_CLASSES_SCHEMA,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback

from .const import (
    CONF_ALT_NIGHT_MODE,
    CONF_AUTO_BYPASS,
    CONF_CODE_ARM_REQUIRED,
    CONF_RELAY_ADDR,
    CONF_RELAY_CHAN,
    CONF_ZONE_LOOP,
    CONF_ZONE_NAME,
    CONF_ZONE_NUMBER,
    CONF_ZONE_RFID,
    CONF_ZONE_TYPE,
    DEFAULT_ARM_OPTIONS,
    DEFAULT_DEVICE_HOST,
    DEFAULT_DEVICE_PORT,
    DEFAULT_ZONE_OPTIONS,
    DEFAULT_ZONE_TYPE,
    DOMAIN,
    CONF_MODELO,
    OPTIONS_ARM,
    OPTIONS_ZONES,
)

EDIT_KEY = "edit_selection"
EDIT_ZONES = "Zones"
EDIT_SETTINGS = "Arming Settings"

_LOGGER = logging.getLogger(__name__)


class AlarmDecoderFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a JFL Active config flow."""

    VERSION = 1

    def __init__(self):
        """Initialize JFL Active ConfigFlow."""

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AlarmDecoderOptionsFlowHandler:
        """Get the options flow for JFL Active20."""
        return AlarmDecoderOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle JFL Active 20 setup."""
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
                _LOGGER.info("Connection from JFL Active20 possible")
                return self.async_create_entry(
                    title=title, data={**connection}
                )
            except OSError as err:
                _LOGGER.debug("error:%s",err)
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during JFL Active20 setup")
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


class AlarmDecoderOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle JFL Active options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize AlarmDecoder options flow."""
        self.arm_options = config_entry.options.get(OPTIONS_ARM, DEFAULT_ARM_OPTIONS)
        self.zone_options = config_entry.options.get(
            OPTIONS_ZONES, DEFAULT_ZONE_OPTIONS
        )
        self.selected_zone = None

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            if user_input[EDIT_KEY] == EDIT_SETTINGS:
                return await self.async_step_arm_settings()
            if user_input[EDIT_KEY] == EDIT_ZONES:
                return await self.async_step_zone_select()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(EDIT_KEY, default=EDIT_SETTINGS): vol.In(
                        [EDIT_SETTINGS, EDIT_ZONES]
                    )
                },
            ),
        )

    async def async_step_arm_settings(self, user_input=None):
        """Arming options form."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={OPTIONS_ARM: user_input, OPTIONS_ZONES: self.zone_options},
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
                },
            ),
        )

    async def async_step_zone_select(self, user_input=None):
        """Zone selection form."""
        errors = _validate_zone_input(user_input)

        if user_input is not None and not errors:
            self.selected_zone = str(
                int(user_input[CONF_ZONE_NUMBER])
            )  # remove leading zeros
            return await self.async_step_zone_details()

        return self.async_show_form(
            step_id="zone_select",
            data_schema=vol.Schema({vol.Required(CONF_ZONE_NUMBER): str}),
            errors=errors,
        )

    async def async_step_zone_details(self, user_input=None):
        """Zone details form."""
        errors = _validate_zone_input(user_input)

        if user_input is not None and not errors:
            zone_options = self.zone_options.copy()
            zone_id = self.selected_zone
            zone_options[zone_id] = _fix_input_types(user_input)

            # Delete zone entry if zone_name is omitted
            if CONF_ZONE_NAME not in zone_options[zone_id]:
                zone_options.pop(zone_id)

            return self.async_create_entry(
                title="",
                data={OPTIONS_ARM: self.arm_options, OPTIONS_ZONES: zone_options},
            )

        existing_zone_settings = self.zone_options.get(self.selected_zone, {})

        return self.async_show_form(
            step_id="zone_details",
            description_placeholders={CONF_ZONE_NUMBER: self.selected_zone},
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ZONE_NAME,
                        description={
                            "suggested_value": existing_zone_settings.get(
                                CONF_ZONE_NAME
                            )
                        },
                    ): str,
                    vol.Optional(
                        CONF_ZONE_TYPE,
                        default=existing_zone_settings.get(
                            CONF_ZONE_TYPE, DEFAULT_ZONE_TYPE
                        ),
                    ): BINARY_SENSOR_DEVICE_CLASSES_SCHEMA,
                    vol.Optional(
                        CONF_ZONE_RFID,
                        description={
                            "suggested_value": existing_zone_settings.get(
                                CONF_ZONE_RFID
                            )
                        },
                    ): str,
                    vol.Optional(
                        CONF_ZONE_LOOP,
                        description={
                            "suggested_value": existing_zone_settings.get(
                                CONF_ZONE_LOOP
                            )
                        },
                    ): str,
                    vol.Optional(
                        CONF_RELAY_ADDR,
                        description={
                            "suggested_value": existing_zone_settings.get(
                                CONF_RELAY_ADDR
                            )
                        },
                    ): str,
                    vol.Optional(
                        CONF_RELAY_CHAN,
                        description={
                            "suggested_value": existing_zone_settings.get(
                                CONF_RELAY_CHAN
                            )
                        },
                    ): str,
                }
            ),
            errors=errors,
        )


def _validate_zone_input(zone_input):
    if not zone_input:
        return {}
    errors = {}

    # CONF_RELAY_ADDR & CONF_RELAY_CHAN are inclusive
    if (CONF_RELAY_ADDR in zone_input and CONF_RELAY_CHAN not in zone_input) or (
        CONF_RELAY_ADDR not in zone_input and CONF_RELAY_CHAN in zone_input
    ):
        errors["base"] = "relay_inclusive"

    # The following keys must be int
    for key in (CONF_ZONE_NUMBER, CONF_ZONE_LOOP, CONF_RELAY_ADDR, CONF_RELAY_CHAN):
        if key in zone_input:
            try:
                int(zone_input[key])
            except ValueError:
                errors[key] = "int"

    # CONF_ZONE_LOOP depends on CONF_ZONE_RFID
    if CONF_ZONE_LOOP in zone_input and CONF_ZONE_RFID not in zone_input:
        errors[CONF_ZONE_LOOP] = "loop_rfid"

    # CONF_ZONE_LOOP must be 1-4
    if (
        CONF_ZONE_LOOP in zone_input
        and zone_input[CONF_ZONE_LOOP].isdigit()
        and int(zone_input[CONF_ZONE_LOOP]) not in list(range(1, 5))
    ):
        errors[CONF_ZONE_LOOP] = "loop_range"

    return errors


def _fix_input_types(zone_input):
    """Convert necessary keys to int.

    Since ConfigFlow inputs of type int cannot default to an empty string, we collect the values below as
    strings and then convert them to ints.
    """

    for key in (CONF_ZONE_LOOP, CONF_RELAY_ADDR, CONF_RELAY_CHAN):
        if key in zone_input:
            zone_input[key] = int(zone_input[key])

    return zone_input


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
