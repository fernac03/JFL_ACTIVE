"""Support for AlarmDecoder sensors (Shows Panel Display)."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.siren import (
    ATTR_DURATION,
    DOMAIN,
    SirenEntity,
    SirenEntityFeature,
)
import logging
from typing import Any
from .const import SIGNAL_PANEL_MESSAGE

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up for JFL Active sensor."""


    entity = JFLActiveSensor()
    async_add_entities([entity])
    entity = JFLActiveBattery()
    async_add_entities([entity])
    entity = JFLActiveSiren()
    async_add_entities([entity])
    entity = JFLActivePartition()
    async_add_entities([entity])
    entity = JFLActiveEletricFecnce()
    async_add_entities([entity])


class JFLActiveSensor(SensorEntity):
    """Representation of an JFL Active keypad."""

    _attr_icon = "mdi:alarm-check"
    _attr_name = "Alarm Panel Display"
    _attr_should_poll = False
    _attr_unique_id = "JFLActive_KEYPAD"
    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_PANEL_MESSAGE, self._message_callback
            )
        )

    def _message_callback(self, message):
        if self._attr_native_value != message.text:
            self._attr_native_value = message.text
            self.schedule_update_ha_state()
class JFLActiveBattery(SensorEntity):
    """Representation of an JFL Active Batery."""
    
    _attr_icon = "mdi:battery-10"
    _attr_name = "Alarm Panel Baterry"
    _attr_should_poll = True
    _attr_unique_id = "JFLActive_Battery"
    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_PANEL_MESSAGE, self._message_callback
            )
        )

    def _message_callback(self, message):
        if message.battery_low:
            self._attr_icon = "mdi:battery-10"
            self._attr_native_value = "Low"
            self.schedule_update_ha_state()
        else:
            self._attr_icon = "mdi:battery"
            self._attr_native_value = "Charged"
            self.schedule_update_ha_state()

class JFLActiveSiren(SirenEntity):

    """Representation of an JFL Active Siren."""
    _attr_icon = "mdi:alarm-bell"
    _attr_name = "Alarm Panel Siren A"
    _attr_should_poll = True
    _attr_unique_id = "JFLActive_SIREN"
    _attr_supported_features = (
            SirenEntityFeature.TURN_ON | SirenEntityFeature.TURN_OFF
    )

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_PANEL_MESSAGE, self._message_callback
            )
        )
    def _message_callback(self, message):
        if message.alarm_sounding:
            self._attr_is_on = True
            self.async_write_ha_state()
        else:
            self._attr_is_on = False
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.call_state_change(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.call_state_change(False)

class JFLActivePartition(SensorEntity):
    """Representation of an JFL Active Eletric Fence."""

    _attr_icon = "mdi:collage"
    _attr_name = "Partition"
    _attr_should_poll = False
    _attr_unique_id = "JFLActive_Partition"
    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_PANEL_MESSAGE, self._message_callback
            )
        )

    def _message_callback(self, message):
        if message.CONF_PARTITION:
            self._attr_native_value = True
            self.schedule_update_ha_state()
        else:
            self._attr_native_value = False
            self.schedule_update_ha_state()
            
class JFLActiveEletricFecnce(SensorEntity):
    """Representation of an JFL Active Eletric Fence."""

    _attr_icon = "mdi:flash"
    _attr_name = "Eletric Fence"
    _attr_should_poll = False
    _attr_unique_id = "JFLActive_EletricFence"
    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_PANEL_MESSAGE, self._message_callback
            )
        )

    def _message_callback(self, message):
        if message.eletrificador==True:
            self._attr_native_value = True
            self.schedule_update_ha_state()
        else:
            self._attr_native_value = False
            self.schedule_update_ha_state()