import logging
from datetime import timedelta
import asyncio
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import HomeAssistant
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)
@dataclass
class SharedData:
    binary_sensor_data: dict = None
    switch_data: dict = None
    sensor_data: dict = None

class AlarmServerCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, alarm_server):
        super().__init__(
            hass,
            _LOGGER,
            name="alarm_server",
            update_method=self._async_update_data,
        )
        self.alarm_server = alarm_server
        self.alarm_server.register_callback(self._async_request_refresh)
        self.data = SharedData()

    async def _async_update_data(self):
        try:
            # Obtém os estados de todos os sensores
            binary_sensor_states = await self.hass.async_add_executor_job(self.alarm_server.get_all_binary_sensor_states)
            switch_states = await self.hass.async_add_executor_job(self.alarm_server.get_all_switch_states)
            sensor_states = await self.hass.async_add_executor_job(self.alarm_server.get_all_sensor_states)
            binary_sensor_data = {}
            for zona_id, binary_sensor_info in binary_sensor_states.items():
                binary_sensor_data[zona_id] = {
                    "state": binary_sensor_info['state'],
                    "name": binary_sensor_info['name']
                }
            switch_data={}
            for switch_id , switch_info in switch_states.items():
                switch_data[switch_id] = {
                    "state": switch_info['state'],
                    "name": switch_info['name'],
                    "type": switch_info['type'],
                    "tipo": switch_info['tipo'],
                    "switch_number": switch_info['switch_number']
                }
            sensor_data = {}
            for sensor_id, sensor_info in sensor_states.items():
                sensor_data[sensor_id] = {
                    "state": sensor_info['state'],
                    "name":  sensor_info['name'],
                    "device_class":  sensor_info['device_class']
                } 
            self.data.binary_sensor_data=binary_sensor_data
            self.data.switch_data = switch_data
            self.data.sensor_data = sensor_data
            # Atualiza as entidades existentes
            if hasattr(self.alarm_server, 'entities'):
                for entity in self.alarm_server.entities:
                    try:
                        if entity.unique_id in self.data.binary_sensor_data:
                           new_state = self.data.binary_sensor_data.get(entity.unique_id, False).get("state")       
                        elif entity.unique_id in self.data.switch_data:
                           new_state = self.data.switch_data.get(entity.unique_id, False).get("state")       
                        elif entity.unique_id in self.data.sensor_data:
                           new_state = self.data.sensor_data.get(entity.unique_id, False).get("state")       
                        else:
                           new_state =entity.state
                        
                        if entity.state != new_state:
                          if hasattr(entity, 'async_schedule_update_ha_state'):
                              entity._attr_state = new_state 
                              if asyncio.iscoroutinefunction(entity.async_schedule_update_ha_state):
                                  await entity.async_schedule_update_ha_state(True)
                              else:
                                  entity.async_schedule_update_ha_state(True)
                          else:
                              # Tentativa de atualização manual
                              if isinstance(entity, Entity):
                                  entity._async_write_ha_state()
                    except Exception as e:
                        _LOGGER.error(f'Erro ao atualizar {entity.unique_id}: {str(e)}')
                        _LOGGER.error(f'Tipo da entidade: {type(entity)}')
                        _LOGGER.error(f'Atributos da entidade: {dir(entity)}')
            return self.data
        except Exception as err:
            raise ConfigEntryNotReady from err
    
    async def async_unload(self):
        """Unload the coordinator."""
        self.alarm_server.remove_callback(self.async_request_refresh)
    async def _async_request_refresh(self):
        """Request a refresh."""
        await self.async_request_refresh()
    
