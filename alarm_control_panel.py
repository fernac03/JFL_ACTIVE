"""Support for JFL Active20 alarm control panels. """
from __future__ import annotations

import voluptuous as vol
import logging
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_CODE,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ALT_NIGHT_MODE,
    CONF_AUTO_BYPASS,
    CONF_PARTITION,
    CONF_CODE_ARM_REQUIRED,
    DATA_AD,
    DEFAULT_ARM_OPTIONS,
    DOMAIN,
    CONF_MODELO,
    OPTIONS_ARM,
    SIGNAL_PANEL_MESSAGE,
)
_LOGGER = logging.getLogger(__name__)
SERVICE_ALARM_TOGGLE_CHIME = "alarm_toggle_chime"

SERVICE_ALARM_KEYPRESS = "alarm_keypress"
ATTR_KEYPRESS = "keypress"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up for JFL Active20 alarm panels."""
    options = entry.options
    arm_options = options.get(OPTIONS_ARM, DEFAULT_ARM_OPTIONS)
    client = hass.data[DOMAIN][entry.entry_id][DATA_AD]

    entity = AlarmDecoderAlarmPanel(
        client=client,
        auto_bypass=arm_options[CONF_AUTO_BYPASS],
        code_arm_required=arm_options[CONF_CODE_ARM_REQUIRED],
        alt_night_mode=arm_options[CONF_ALT_NIGHT_MODE],
    )
    async_add_entities([entity])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_ALARM_TOGGLE_CHIME,
        {
            vol.Required(ATTR_CODE): cv.string,
        },
        "alarm_toggle_chime",
    )

    platform.async_register_entity_service(
        SERVICE_ALARM_KEYPRESS,
        {
            vol.Required(ATTR_KEYPRESS): cv.string,
        },
        "alarm_keypress",
    )


class AlarmDecoderAlarmPanel(AlarmControlPanelEntity):
    """Representation of an JFL Active20 alarm panel."""

    _attr_name = "Alarm Panel"
    _attr_should_poll = False
    _attr_code_format = CodeFormat.NUMBER
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )

    def __init__(self, client, auto_bypass, code_arm_required, alt_night_mode):
        """Initialize the alarm panel."""
        self._client = client
        self._code = "0839"
        self._auto_bypass = auto_bypass
        self._attr_code_arm_required = code_arm_required
        self._alt_night_mode = alt_night_mode

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_PANEL_MESSAGE, self._message_callback
            )
        )

    def _message_callback(self, message):
        """Handle received messages."""
        if message.alarm_sounding or message.fire_alarm:
            self._attr_state = STATE_ALARM_TRIGGERED
        elif message.armed_away:
            self._attr_state = STATE_ALARM_ARMED_AWAY
        else:
            self._attr_state = STATE_ALARM_DISARMED

        self._attr_extra_state_attributes = {
            "ac_power": message.ac_power,
            "alarm_event_occurred": message.alarm_event_occurred,
            "backlight_on": message.backlight_on,
            "battery_low": message.battery_low,
            "check_zone": message.check_zone,
            "chime": message.chime_on,
            "entry_delay_off": message.entry_delay_off,
            "programming_mode": message.programming_mode,
            "ready": message.ready,
            "zone_bypassed": message.zone_bypassed,
        }
        self.schedule_update_ha_state()
    def checksum(self,dados):
        #checksum = 0
        #for el in dados:
        #   checksum ^= ord(el)
        checksum = 0
        for n  in dados:
            checksum ^= n
        return checksum
    def alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        if not self._validate_code(code, STATE_ALARM_DISARMED):
            return
        if CONF_PARTITION:
           message = b'\xB3\x36\x02\x00\x00\x00\x00'
           check = self.checksum(message)
           message += check.to_bytes(2,'big')
           #self._client.put(bytes(message))
           message = b'\xB3\x36\x02\x01\x00\x00\x00'
           check = slef.checksum(message)
           message += check.to_bytes(2,'big')
           #self._client.put(bytes(message))
           _LOGGER.info("particionada desarmando as duas particoes")
        else:
           message = b'\xB3\x36\x02\x00\x00\x00\x00'
           check = self.checksum(message)
           message += check.to_bytes(2,'big')
           #self._client.put(bytes(message))
           _LOGGER.info("sem particcao desarmando particao A")

    def alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        if self.code_arm_required and not self._validate_code(code, STATE_ALARM_ARMED_AWAY):
            return
        _LOGGER.info('particionada %s',CONF_PARTITION)
        _LOGGER.info('modelo %s',CONF_MODELO)


        if CONF_PARTITION:
           message = b'\xB3\x36\x01\x00\x00\x00\x00'
           check = self.checksum(message)
           message += check.to_bytes(2,'big')
           #self._client.put(bytes(message))
           message = b'\xB3\x36\x01\x01\x00\x00\x00'
           check = self.checksum(message)
           message += check.to_bytes(2,'big')
           #self._client.put(bytes(message))
           _LOGGER.info("particionada armando as duas particoes away")
        else:
           message = b'\xB3\x36\x01\x00\x00\x00\x00'
           check = self.checksum(message)
           message += check.to_bytes(2,'big')
           #self._client.put(bytes(message))
           _LOGGER.info("sem particao armando particao a %s" ,message)

    def alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        if self.code_arm_required and not self._validate_code(code, STATE_ALARM_ARMED_HOME):
            return
        _LOGGER.info('particionada %s',CONF_PARTITION)
        if CONF_PARTITION:
           message = b'\xB3\x36\x01\x01\x00\x00\x00'
           check = self.checksum(message)
           message += check.to_bytes(2,'big')
           #self._client.put(bytes(message))
           _LOGGER.info("particao armando particao B stay")
        else:
           message = b'\xB3\x36\x01\x00\x00\x00\x00'
           check = self.checksum(message)
           message += check.to_bytes(2,'big')
           #self._client.put(bytes(message))
           _LOGGER.info("sem particao armando particao a")



    def alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command."""
        if self.code_arm_required and not self._validate_code(code, STATE_ALARM_ARMED_HOME):
            return
        _LOGGER.info('particionada %s',CONF_PARTITION)
        if CONF_PARTITION:
           message = b'\xB3\x36\x01\x00\x00\x00\x00'
           check = self.checksum(message)
           message += check.to_bytes(2,'big')
           self._client.put(bytes(message))
           message = b'\xB3\x36\x01\x01\x00\x00\x00'
           check = self.checksum(message)
           message += check.to_bytes(2,'big')
           #self._client.put(bytes(message))
        else:
           message = b'\xB3\x36\x01\x00\x00\x00\x00'
           check = self.checksum(message)
           message += check.to_bytes(2,'big')
           #self._client.put(bytes(message))


    def alarm_toggle_chime(self, code=None):
        """Send toggle chime command."""
        if code:
            self._client.send(f"{code!s}9")

    def alarm_keypress(self, keypress):
        """Send custom keypresses."""
        if keypress:
            self._client.send(keypress)
    def _validate_code(self, code, state):
        """Validate given code."""
        if self._code is None:
            return True
        if isinstance(self._code, str):
            alarm_code = self._code
        else:
            alarm_code = self._code.render(
                parse_result=False, from_state=self._state, to_state=state
            )
        check = not alarm_code or code == alarm_code
        if not check:
            _LOGGER.warning("Invalid code given for %s", state)
        return check