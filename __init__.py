# __init__.py
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
from .const import DOMAIN, MANUFACTURER
from .alarm_server import AlarmServer
from .alarm_coordinator import AlarmServerCoordinator
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
    ATTR_CODE,
    STATE_UNKNOWN,
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_PROBLEM,
    ATTR_ENTITY_ID,
)

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    config_entry_id = entry.entry_id

    alarm_server = AlarmServer(hass, entry.data["host"], entry.data["port"],config_entry_id)
    if not hasattr(alarm_server, 'entities'):
        alarm_server.entities = []
    coordinator = AlarmServerCoordinator(hass, alarm_server)
    await coordinator.async_config_entry_first_refresh()
    await hass.async_add_executor_job(alarm_server.start)
    hass.data[DOMAIN][entry.entry_id] = alarm_server
    hass.data[DOMAIN][entry.entry_id].coordinator= coordinator
    # Registrar o dispositivo da central de alarme
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, alarm_server.unique_id)},
        name="Central de Alarme",
        manufacturer=MANUFACTURER,
        model=alarm_server.model,
        sw_version=alarm_server.sw_version,
    )    
    
    hass.data[DOMAIN][entry.entry_id].device_id = device.id
    #hass.async_create_task(
    #     hass.config_entries.async_forward_entry_setups(entry, "alarm_control_panel")
    #)
    #hass.async_create_task(
    #    hass.config_entries.async_forward_entry_setups(entry, "sensor")
    #)
    #hass.async_create_task(
    #    hass.config_entries.async_forward_entry_setups(entry, "binary_sensor")
    #)
    
    #hass.async_create_task(
    #     hass.config_entries.async_forward_entry_setups(entry, "switch")
#
 #   )
  # Setup das plataformas
    await hass.config_entries.async_forward_entry_setups(
        entry, 
        ["alarm_control_panel", "sensor", "binary_sensor", "switch"]
    )  
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    # Implementar a lógica de descarregamento da integração
    hass.data.setdefault(DOMAIN, {})
    config_entry_id = entry.entry_id
    alarm_server = AlarmServer(hass, entry.data["host"], entry.data["port"],config_entry_id)
    await hass.async_add_executor_job(alarm_server.stop())
    pass

