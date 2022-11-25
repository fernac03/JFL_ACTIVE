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
    """Set up for JFL Active20 sensor."""


    entity = JFLActive20Sensor()
    async_add_entities([entity])
    entity = JFLActive20Battery()
    async_add_entities([entity])
    entity = JFLActive20Siren()
    async_add_entities([entity])


class JFLActive20Sensor(SensorEntity):
    """Representation of an JFL Active20 keypad."""

    _attr_icon = "mdi:alarm-check"
    _attr_name = "Alarm Panel Display"
    _attr_should_poll = False

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

class JFLActive20Battery(SensorEntity):
    """Representation of an JFL Active20 Batery."""
    
    _attr_icon = "mdi:battery-10"
    _attr_name = "Alarm Panel Baterry"
    _attr_should_poll = True

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

class JFLActive20Siren(SirenEntity):
    """Representation of an JFL Active20 Siren."""
    _attr_icon = "mdi:alarm-bell"
    _attr_name = "Alarm Panel Siren A"
    _attr_should_poll = True
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
