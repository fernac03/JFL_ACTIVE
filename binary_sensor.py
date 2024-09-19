# binary_sensor.py
import asyncio
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from .alarm_coordinator import AlarmServerCoordinator
#from homeassistant.core import HomeAssistant, Event
#from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.entity import async_generate_entity_id

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_UNKNOWN,
)
from datetime import timedelta
import logging
from .const import DOMAIN
ENTITY_ID_FORMAT = 'binary_sensor.{}'
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    alarm_server = hass.data[DOMAIN][config_entry.entry_id]
    device_id = alarm_server.device_id
    coordinator = hass.data[DOMAIN][config_entry.entry_id].coordinator
    _LOGGER.warn("aqui no async_setup do sensor")
    created_sensors = {}
    async def async_add_binary_sensors():
        new_binary_sensors = []
        binary_sensor_states = await hass.async_add_executor_job(alarm_server.get_all_binary_sensor_states)
        for zone_id,zone_data in binary_sensor_states.items():
            # Gere um ID de entidade único
            unique_id = f"{alarm_server.device_id}_{zone_id}"
            entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, f"zona_{zone_id}", hass=hass)
            # Verifique se o sensor já existe
            if unique_id not in created_sensors:
                new_sensor = AlarmBinarySensor(coordinator, alarm_server, zone_id, zone_data["name"], unique_id, entity_id, BinarySensorDeviceClass.OPENING)
                new_binary_sensors.append(new_sensor)
                created_sensors[unique_id] = new_sensor
                alarm_server.entities.append(new_sensor)
        if new_binary_sensors:
            async_add_entities(new_binary_sensors)

    await async_add_binary_sensors()
    # Configura um listener para adicionar novos sensores quando a central se reconectar
    async def async_central_updated(event):
        await coordinator.async_request_refresh()
        await async_add_binary_sensors()

    hass.bus.async_listen("alarm_central_updated", async_central_updated)



class AlarmBinarySensor(CoordinatorEntity, Entity):
    def __init__(self, coordinator, alarm_server, unique_id, name, device_id, zone_number, device_class):
        super().__init__(coordinator)
        self._alarm_server = alarm_server
        self._unique_id = unique_id
        self._name = name
        self._device_id = device_id
        self._zone_number = zone_number
        self._device_class = device_class
    @property
    def unique_id(self):
        return f"{self._unique_id}"

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self.coordinator.data.binary_sensor_data.get(self._unique_id, False).get("state")       
    @property
    def device_class(self):
        return self._device_class

    @property
    def extra_state_attributes(self):
         return self.coordinator.data.binary_sensor_data.get(self.entity_id, {}).get("attributes", {})        
    
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._alarm_server.unique_id)},
            "via_device": (DOMAIN, self._alarm_server.unique_id),
        }
    async def async_turn_on(self, **kwargs):
        #await self._alarm_server.send_command(f"switch_on_{self._switch_id}")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        #await self._alarm_server.send_command(f"switch_off_{self._switch_id}")
        await self.coordinator.async_request_refresh()

