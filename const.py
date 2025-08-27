"""Constants for the JFL Alarm integration."""

DOMAIN = "jfl_alarm"

# Configuration
CONF_KEEP_ALIVE_INTERVAL = "keep_alive_interval"
CONF_ENABLE_KEEP_ALIVE = "enable_keep_alive"
CONF_GET_STATE_INTERVAL = "get_state_interval"
CONF_ENABLE_GET_STATE = "enable_get_state"

# Defaults
DEFAULT_PORT = 9999
DEFAULT_HOST = "0.0.0.0"
DEFAULT_KEEP_ALIVE_INTERVAL = 30000
DEFAULT_GET_STATE_INTERVAL = 5000

# Alarm Commands
ALARM_COMMANDS = {
    "ARM_AWAY": [0x06, 0x01, 0x4E, 0x01],
    "ARM_STAY": [0x06, 0x01, 0x53, 0x01],
    "DISARM": [0x06, 0x01, 0x4F, 0x01],
    "PGM_ON": [0x06, 0x01, 0x50],  # + pgm_number
    "PGM_OFF": [0x06, 0x01, 0x51],  # + pgm_number
}

# JFL Models
JFL_MODELS = {
    0xA0: {
        "name": "Active-32 Duo",
        "eletrificador": True,
        "pgms": 4,
        "particoes": 4,
        "zonas": 32,
    },
    0xA1: {
        "name": "Active 20 Ultra/GPRS",
        "eletrificador": True,
        "pgms": 4,
        "particoes": 2,
        "zonas": 22,
    },
    0xA2: {
        "name": "Active 8 Ultra",
        "eletrificador": False,
        "pgms": 0,
        "particoes": 2,
        "zonas": 12,
    },
    0xA3: {
        "name": "Active 20 Ethernet",
        "eletrificador": True,
        "pgms": 4,
        "particoes": 2,
        "zonas": 22,
    },
    0xA4: {
        "name": "Active 100 Bus",
        "eletrificador": True,
        "pgms": 16,
        "particoes": 16,
        "zonas": 99,
    },
    0xA5: {
        "name": "Active 20 Bus",
        "eletrificador": True,
        "pgms": 16,
        "particoes": 2,
        "zonas": 32,
    },
    0xA6: {
        "name": "Active Full 32",
        "eletrificador": False,
        "pgms": 16,
        "particoes": 4,
        "zonas": 32,
    },
    0xA7: {
        "name": "Active 20",
        "eletrificador": True,
        "pgms": 4,
        "particoes": 2,
        "zonas": 32,
    },
    0xA8: {
        "name": "Active 8W",
        "eletrificador": True,
        "pgms": 4,
        "particoes": 2,
        "zonas": 32,
    },
    0x4B: {
        "name": "M-300+",
        "eletrificador": False,
        "pgms": 4,
        "particoes": 0,
        "zonas": 0,
    },
    0x5D: {
        "name": "M-300 Flex",
        "eletrificador": False,
        "pgms": 2,
        "particoes": 0,
        "zonas": 0,
    },
}

# Event codes mapping
EVENT_CODES = {
    # Arming events
    "3441": {"state": "ARMED_STAY", "description": "Sistema armado parcialmente"},
    "3401": {"state": "ARMED_HOME", "description": "Sistema armado"},
    "3407": {"state": "ARMED_HOME", "description": "Sistema armado"},
    "3403": {"state": "ARMED_HOME", "description": "Autoarme por horário programado"},
    "3404": {"state": "ARMED_HOME", "description": "Autoarme por não movimento"},
    "3408": {"state": "ARMED_HOME", "description": "Arme rápido"},
    "3409": {"state": "ARMED_HOME", "description": "Sistema armado totalmente"},
    
    # Disarming events
    "1401": {"state": "DISARMED", "description": "Sistema desarmado"},
    "1407": {"state": "DISARMED", "description": "Desarme remoto"},
    "1403": {"state": "DISARMED", "description": "Auto-desarme por horário programado"},
    "1409": {"state": "DISARMED", "description": "Desarme por controle remoto ou entrada LIGA"},
    
    # Emergency events
    "1100": {"state": "EMERGENCY", "description": "Emergência Médica"},
    "1101": {"state": "FIRE", "description": "Alarme de Incêndio"},
    "1102": {"state": "PANIC", "description": "Pânico"},
    
    # Alarm events
    "1103": {"state": "ALARM_SOUNDING", "description": "Alarme zona"},
    "1104": {"state": "ALARM_SOUNDING", "description": "Alarme zona"},
    "1105": {"state": "ALARM_SOUNDING", "description": "Alarme zona"},
    "1106": {"state": "ALARM_SOUNDING", "description": "Alarme zona"},
    "1107": {"state": "ALARM_SOUNDING", "description": "Alarme zona"},
    "1108": {"state": "ALARM_SOUNDING", "description": "Alarme zona"},
    "1109": {"state": "ALARM_SOUNDING", "description": "Alarme zona"},
    
    # PGM events
    "1422": {"state": "PGM_ON", "description": "PGM acionada pelo usuário"},
    "3422": {"state": "PGM_OFF", "description": "PGM desacionada pelo usuário"},
    
    # Zone events
    "1130": {"state": "ZONE_TRIGGER", "description": "Disparo de zona"},
    "1134": {"state": "ZONE_TRIGGER", "description": "Disparo de zona"},
    "1137": {"state": "ZONE_TAMPER", "description": "Alarme de zona tipo tamper"},
    "3130": {"state": "ZONE_RESTORE", "description": "Restauração do disparo da zona"},
    "3134": {"state": "ZONE_RESTORE", "description": "Restauração do alarme de porta aberta"},
    "3137": {"state": "ZONE_RESTORE", "description": "Restauração do alarme de zona tipo tamper"},
    
    # Battery events
    "1384": {"state": "BATTERY_LOW", "description": "Bateria baixa"},
    "3384": {"state": "BATTERY_OK", "description": "Bateria restaurada"},
    
    # AC Power events
    "1301": {"state": "AC_FAIL", "description": "Falha de energia AC"},
    "3301": {"state": "AC_OK", "description": "Energia AC restaurada"},
    
    # Test events
    "1602": {"state": "TEST", "description": "Teste periódico realizado"},
}

# Zone status mapping
ZONE_STATUS_MAP = {
    0: "disabled",
    1: "inhibited",
    2: "triggered",
    3: "no_communication",
    4: "short_circuit",
    5: "tamper_open",
    6: "low_battery",
    7: "open",
    8: "closed",
}

# Services
SERVICE_ARM_AWAY = "arm_away"
SERVICE_ARM_HOME = "arm_home"
SERVICE_DISARM = "disarm"
SERVICE_PGM_ON = "pgm_on"
SERVICE_PGM_OFF = "pgm_off"

# Attributes
ATTR_PGM_NUMBER = "pgm_number"
ATTR_CODE = "code"
