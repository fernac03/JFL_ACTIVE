# alarm_panel.py
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
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)
from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
    SUPPORT_ALARM_ARM_NIGHT,
    SUPPORT_ALARM_TRIGGER,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import ConfigEntryNotReady
from .const import (
    CONF_ALT_NIGHT_MODE,
    CONF_AUTO_BYPASS,
    CONF_CODE_REQUIRED,
    CONF_CODE_ARM_REQUIRED,
    DEFAULT_ARM_OPTIONS,
    DOMAIN,
    OPTIONS_ARM,
    SIGNAL_PANEL_MESSAGE,
)
_LOGGER = logging.getLogger(__name__)
SERVICE_ALARM_COMMAND= "alarm_COMMAND"



class AlarmPanel(AlarmControlPanelEntity):
    _attr_name = "Alarm Panel"
    _attr_should_poll = False
    _attr_code_format = CodeFormat.NUMBER
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )
    def __init__(self, hass, alarm_server, name,auto_bypass,code_arm_required,alt_night_mode,code_required):
        self._hass = hass
        self._alarm_server = alarm_server
        self._name = name
        self._state = STATE_ALARM_DISARMED
        self._code = code_required
        self._auto_bypass = auto_bypass
        self._attr_code_arm_required = code_arm_required
        self._alt_night_mode = alt_night_mode
    
    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def supported_features(self):
        return SUPPORT_ALARM_ARM_AWAY | SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_NIGHT | SUPPORT_ALARM_TRIGGER
    
    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_PANEL_MESSAGE, self._message_callback
            )
        )

    def _message_callback(self, message):
        """Handle received messages."""
        _LOGGER.warn('##############################message########################')
        _LOGGER.warn(f'## {message.status_alarm}')
        if message.alarm_sounding or message.fire_alarm:
           self._attr_state = STATE_ALARM_TRIGGERED
           _LOGGER.warn("disparo de alarme sirene ativada")
        elif message.armed_away:
           self._attr_state = STATE_ALARM_ARMED_AWAY
           _LOGGER.warn("mensagem armed_AWAY")
        elif message.armed_home:
           self._attr_state = STATE_ALARM_ARMED_HOME
           _LOGGER.warn("mensagem armed_home")
        elif message.armed_night:
           self._attr_state = STATE_ALARM_ARMED_NIGHT
           _LOGGER.warn("mensagem armed_night")
        else:
           self._attr_state = STATE_ALARM_DISARMED
           _LOGGER.warn("mensagem disarmed")
        self.schedule_update_ha_state()

    async def async_alarm_disarm(self, code=None):
        if self.code_arm_required and not self._validate_code(code, STATE_ALARM_DISARMED):
            return
        # Implementar lógica para desarmar o alarme
        self._alarm_server.send_command("disarm")
        #self._state = STATE_ALARM_DISARMED
        #self.async_write_ha_state()

    async def async_alarm_arm_away(self, code=None):
        if self.code_arm_required and not self._validate_code(code, STATE_ALARM_ARMED_AWAY):
            return
        # Implementar lógica para armar o alarme no modo "away"
        self._alarm_server.send_command("arm_away")
        #self._state = STATE_ALARM_ARMED_AWAY
        #self.async_write_ha_state()

    async def async_alarm_arm_home(self, code=None):
        if self.code_arm_required and not self._validate_code(code, STATE_ALARM_ARMED_HOME):
            return
        # Implementar lógica para armar o alarme no modo "home"
        self._alarm_server.send_command("arm_home")
        #self._state = STATE_ALARM_ARMED_HOME
        #self.async_write_ha_state()

    async def async_alarm_arm_night(self, code=None):
        if self.code_arm_required and not self._validate_code(code, STATE_ALARM_ARMED_NIGHT):
            return
        # Implementar lógica para armar o alarme no modo "night"
        self._alarm_server.send_command("arm_night")
        #self._state = STATE_ALARM_ARMED_NIGHT
        #self.async_write_ha_state()

    async def async_alarm_trigger(self, code=None):
        # Implementar lógica para disparar o alarme
        self._alarm_server.send_command("trigger")
        #self._state = STATE_ALARM_TRIGGERED
        #self.async_write_ha_state()
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
            _LOGGER.warn("Invalid code given for %s", state)
        return check

    

async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities) -> None:
    """Set up for JFL Active alarm panels."""
    alarm_server = hass.data[DOMAIN][config_entry.entry_id]
    options = config_entry.options
    arm_options = options.get(OPTIONS_ARM, DEFAULT_ARM_OPTIONS)
    alarm_server = hass.data[DOMAIN][config_entry.entry_id]

    entity = AlarmPanel(hass,alarm_server,"Alarm Panel",
        auto_bypass=arm_options[CONF_AUTO_BYPASS],
        code_arm_required=arm_options[CONF_CODE_ARM_REQUIRED],
        code_required=arm_options[CONF_CODE_REQUIRED],
        alt_night_mode=arm_options[CONF_ALT_NIGHT_MODE],
    )
    async_add_entities([entity])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_ALARM_COMMAND,
        {
            vol.Required(ATTR_CODE): cv.string,
        },
        "alarm_command",
    )

