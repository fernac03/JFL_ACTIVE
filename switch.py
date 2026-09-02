"""Support for JFL Active PGM outputs as switches."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_AD, DOMAIN, SIGNAL_PANEL_MESSAGE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up JFL Active PGM switches."""
    client = hass.data[DOMAIN][entry.entry_id][DATA_AD]
    entities = [JflPgmSwitch(client, pgm_num) for pgm_num in range(1, 9)]
    async_add_entities(entities)


class JflPgmSwitch(SwitchEntity):
    """Representation of a JFL Active PGM output.

    PGM state is read from a bitmask reported periodically by the panel
    (bit N-1 for PGM N) and control commands use the panel's native
    protocol: header 0x7b, length, address 0x01, command byte
    (0x50=on / 0x51=off) and the PGM number, followed by an XOR
    checksum of the preceding bytes.
    """

    _attr_should_poll = False

    def __init__(self, client, pgm_number):
        """Initialize the PGM switch."""
        self._client = client
        self._pgm_number = pgm_number
        self._bit = pgm_number - 1
        self._attr_name = f"PGM {pgm_number}"
        self._attr_icon = "mdi:electric-switch"
        self._attr_unique_id = "JFLActive_PGM_SWITCH_" + str(pgm_number)
        self._attr_is_on = False

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_PANEL_MESSAGE, self._message_callback
            )
        )

    def _message_callback(self, message):
        pgm_status = getattr(message, "pgm_status", None)
        if pgm_status is None:
            return
        new_state = bool(pgm_status & (1 << self._bit))
        if new_state != self._attr_is_on:
            self._attr_is_on = new_state
            self.schedule_update_ha_state()

    def checksum(self, dados):
        checksum = 0
        for n in dados:
            checksum ^= n
        return checksum

    def turn_on(self, **kwargs):
        """Turn the PGM on."""
        message = bytes([0x06, 0x01, 0x50, self._pgm_number])
        check = self.checksum(bytes([0x7B]) + message)
        self._client.put(bytes([0x7B]) + message + check.to_bytes(1, "big"))

    def turn_off(self, **kwargs):
        """Turn the PGM off."""
        message = bytes([0x06, 0x01, 0x51, self._pgm_number])
        check = self.checksum(bytes([0x7B]) + message)
        self._client.put(bytes([0x7B]) + message + check.to_bytes(1, "big"))
