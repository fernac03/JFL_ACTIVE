"""Constants for the JFL  Active 20 Ethernet component."""

CONF_ALT_NIGHT_MODE = "alt_night_mode"
CONF_AUTO_BYPASS = "auto_bypass"
CONF_CODE_ARM_REQUIRED = "code_arm_required"
CONF_RELAY_ADDR = "zone_relayaddr"
CONF_RELAY_CHAN = "zone_relaychan"
CONF_ZONE_LOOP = "zone_loop"
CONF_ZONE_NAME = "zone_name"
CONF_ZONE_NUMBER = "zone_number"
CONF_ZONE_RFID = "zone_rfid"
CONF_ZONE_TYPE = "zone_type"
CONF_PARTITION = False
CONF_MODELO = "Active20"
DATA_AD = "jfl_active20"
DATA_REMOVE_STOP_LISTENER = "rm_stop_listener"
DATA_REMOVE_UPDATE_LISTENER = "rm_update_listener"
DATA_RESTART = "restart"

DEFAULT_ALT_NIGHT_MODE = False
DEFAULT_AUTO_BYPASS = False
DEFAULT_CODE_ARM_REQUIRED = True
DEFAULT_DEVICE_HOST = "localhost"
DEFAULT_DEVICE_PORT = 8085
DEFAULT_ZONE_TYPE = "window"
DEFAULT_CODE = "0000"

DEFAULT_ARM_OPTIONS = {
    CONF_ALT_NIGHT_MODE: DEFAULT_ALT_NIGHT_MODE,
    CONF_AUTO_BYPASS: DEFAULT_AUTO_BYPASS,
    CONF_CODE_ARM_REQUIRED: DEFAULT_CODE_ARM_REQUIRED,
}
DEFAULT_ZONE_OPTIONS: dict = {}

DOMAIN = "jfl_active20"

OPTIONS_ARM = "arm_options"
OPTIONS_ZONES = "zone_options"


SIGNAL_PANEL_MESSAGE = "jfl_active20.panel_message"
SIGNAL_REL_MESSAGE = "jfl_active20.rel_message"
SIGNAL_RFX_MESSAGE = "jfl_active20.rfx_message"
SIGNAL_ZONE_FAULT = "jfl_active20.zone_fault"
SIGNAL_ZONE_RESTORE = "jfl_active20.zone_restore"
