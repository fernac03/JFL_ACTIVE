# switch.py
import asyncio
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .alarm_coordinator import AlarmServerCoordinator

import logging
from datetime import timedelta
from .const import DOMAIN
from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_UNKNOWN,
)
_LOGGER = logging.getLogger(__name__)
ENTITY_ID_FORMAT = 'switch.{}'
class AlarmSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, alarm_server, unique_id, name,device_id):
        super().__init__(coordinator)
        self._alarm_server = alarm_server
        self._unique_id=unique_id
        self._name = name
        self._device_id = device_id
        self._switch_number=0
        self._attr_available = True
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._alarm_server.unique_id)},
            "via_device": (DOMAIN, self._alarm_server.unique_id),
        }
    @property
    def unique_id(self):
        return f"{self._unique_id}"

    @property
    def is_on(self):
        entity_data= self.coordinator.data.switch_data.get(self._unique_id)
        if entity_data:
            return entity_data.get("state") in [True, "on"]
        return False
    @property
    def switch_number(self):
        entity_data= self.coordinator.data.switch_data.get(self._unique_id)
        if entity_data:
            return entity_data.get("switch_number")
        return False
    @property
    def available(self):
        """Retorna se o switch está disponível para uso."""
        return self._attr_available
    async def async_turn_on(self, **kwargs):
        # Implemente a lógica para ligar o switch
        _LOGGER.warn(self.switch_number)
        _LOGGER.warn(kwargs)
        self.coordinator.alarm_server.turn_on_switch(self.switch_number)
        #await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        # Implemente a lógica para desligar o switch
        self.coordinator.alarm_server.turn_off_switch(self.switch_number)
        #await self.coordinator.async_request_refresh()

async def async_setup_entry(hass, config_entry, async_add_entities):
    alarm_server = hass.data[DOMAIN][config_entry.entry_id]
    device_id = alarm_server.device_id
    coordinator = hass.data[DOMAIN][config_entry.entry_id].coordinator
    _LOGGER.warn("aqui no async_setup do switch")
    created_switches = {}

    async def async_add_switches():
        new_switches = []
        switch_states = await hass.async_add_executor_job(alarm_server.get_all_switch_states)
        for switch_id , switch_data in switch_states.items():
            # Gere um ID de entidade único
            unique_id = f"{alarm_server.device_id}_{switch_id}"
            _LOGGER.warn(switch_id)
            entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, f"{switch_data['tipo']}_{switch_id}", hass=hass)
            # Verifique se o sensor já existe
            if unique_id not in created_switches:
                new_switch = AlarmSwitch(coordinator, alarm_server, switch_id, switch_data["name"], unique_id)
                new_switches.append(new_switch)
                created_switches[unique_id] = new_switch
                alarm_server.entities.append(new_switch)
        if new_switches:
            async_add_entities(new_switches)

    await async_add_switches()
    # Configura um listener para adicionar novos sensores quando a central se reconectar
    async def async_central_updated(event):
        await coordinator.async_request_refresh()
        await async_add_switches()

    hass.bus.async_listen("alarm_central_updated", async_central_updated)
