# sensor.py
import asyncio
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .alarm_coordinator import AlarmServerCoordinator
from homeassistant.const import PERCENTAGE
import logging
from datetime import timedelta
from .const import DOMAIN
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelState,
)
from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_UNKNOWN,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
_LOGGER = logging.getLogger(__name__)
ENTITY_ID_FORMAT = 'sensor.{}'

class AlarmSensor(CoordinatorEntity, Entity):
    def __init__(self, coordinator, alarm_server, sensor_id, name,device_id,device_class):
        super().__init__(coordinator)
        self._alarm_server = alarm_server
        self._unique_id = sensor_id	
        self._name = name
        self._device_id = device_id
        self._device_class = None

    @property
    def name(self):
        return self._name
    @property
    def unique_id(self):
        return f"{self._unique_id}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._alarm_server.unique_id)},
            "via_device": (DOMAIN, self._alarm_server.unique_id),
        }
    @property
    def state(self):
        return self.coordinator.data.sensor_data.get(self._unique_id, False).get("state")       

    @property
    def extra_state_attributes(self):
         return self.coordinator.data.sensor_data.get(self._unique_id, {}).get("attributes", {})        

    @property
    def is_on(self):
        return self.state == "on"
    @property
    def device_class(self):
        return self._device_class

class AlarmParticao(CoordinatorEntity, Entity):
    def __init__(self, coordinator, alarm_server, sensor_id, name,device_id,device_class,options: list):
        super().__init__(coordinator)
        self._alarm_server = alarm_server
        self._unique_id = sensor_id	
        self._name = name
        self._device_id = device_id
        self._device_class = None
        self._attr_options = options
        self._attr_state_class = SensorStateClass.MEASUREMENT
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.sensor_data.get(self._unique_id)
    @property

    def name(self):
        return self._name
    @property
    def unique_id(self):
        return f"{self._unique_id}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._alarm_server.unique_id)},
            "via_device": (DOMAIN, self._alarm_server.unique_id),
        }
    @property
    def state(self):
        return self.coordinator.data.sensor_data.get(self._unique_id, False).get("state")       

    @property
    def extra_state_attributes(self):
         return self.coordinator.data.sensor_data.get(self._unique_id, {}).get("attributes", {})        

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "options": self._attr_options,
        }
class AlarmBatterySensor(CoordinatorEntity, Entity):
    def __init__(self, coordinator, alarm_server, sensor_id, name,device_id,device_class):
        super().__init__(coordinator)
        self._alarm_server = alarm_server
        self._unique_id=sensor_id
        self._name = name
        self._device_id = device_id
        self._device_class = SensorDeviceClass.BATTERY
        self._attributes = {}
    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"{self._unique_id}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._alarm_server.unique_id)},
            "via_device": (DOMAIN, self._alarm_server.unique_id),
        }
    @property
    def state(self):
        return self.coordinator.data.sensor_data.get(self._unique_id, False).get("state")       

    @property
    def extra_state_attributes(self):
         return self.coordinator.data.sensor_data.get(self._unique_id, {}).get("attributes", {})        
    
    @property
    def device_class(self):
        return SensorDeviceClass.BATTERY

    @property
    def unit_of_measurement(self):
        return PERCENTAGE

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def state(self):
        return self._attr_state


async def async_setup_entry(hass, config_entry, async_add_entities):
    alarm_server = hass.data[DOMAIN][config_entry.entry_id]
    device_id = alarm_server.device_id
    coordinator = hass.data[DOMAIN][config_entry.entry_id].coordinator
    _LOGGER.warn("aqui no async_setup do sensor")
    created_sensors = {}
    async def async_add_sensors():
        new_sensors = []
        sensor_states = await hass.async_add_executor_job(alarm_server.get_all_sensor_states)
        for sensor_id , sensor_data in sensor_states.items():
            # Gere um ID de entidade único
            unique_id = f"{alarm_server.device_id}_{sensor_id}"
            #_LOGGER.warn(f"id do sensor: {sensor_id}")
            entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, f"_{sensor_id}", hass=hass)
            # Verifique se o sensor já existe
            if unique_id not in created_sensors:
                #_LOGGER.warn(sensor_data["device_class"])
                if sensor_data["device_class"] == SensorDeviceClass.BATTERY:
                   new_sensor = AlarmBatterySensor(coordinator, alarm_server, sensor_id, sensor_data["name"], unique_id,sensor_data["device_class"])
                   #_LOGGER.warn(new_sensor)
                elif sensor_data["device_class"] == "ENUM":
                   new_sensor = AlarmParticao(coordinator, alarm_server, sensor_id, sensor_data["name"], unique_id,sensor_data["device_class"],[STATE_ALARM_ARMED_HOME,STATE_ALARM_ARMED_NIGHT, STATE_ALARM_DISARMED, STATE_ALARM_TRIGGERED])    
                else:
                   new_sensor = AlarmSensor(coordinator, alarm_server, sensor_id, sensor_data["name"], unique_id,sensor_data["device_class"])
                new_sensors.append(new_sensor)
                created_sensors[unique_id] = new_sensor
                alarm_server.entities.append(new_sensor)
        if new_sensors:
            async_add_entities(new_sensors)

    await async_add_sensors()
    # Configura um listener para adicionar novos sensores quando a central se reconectar
    async def async_central_updated(event):
        await coordinator.async_request_refresh()
        await async_add_sensors()

    hass.bus.async_listen("alarm_central_updated", async_central_updated)
