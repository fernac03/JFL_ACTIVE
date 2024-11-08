from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

class MeuDispositivoSwitch(SwitchEntity):
    """Representa um switch do dispositivo."""

    def __init__(self, name):
        self._state = False
        self._name = name

    @property
    def name(self):
        """Nome do switch."""
        return self._name

    @property
    def is_on(self):
        """Retorna o estado do switch."""
        return self._state

    async def async_turn_on(self, **kwargs):
        """Ativa o switch."""
        self._state = True
        await self.async_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """Desativa o switch."""
        self._state = False
        await self.async_update_ha_state()

async def async_setup_entry(hass, config, async_add_entities, discovery_info=None):
    """Configura a plataforma do switch com 2 switches."""
    switches = [
        MeuDispositivoSwitch('Switch 1'),
        MeuDispositivoSwitch('Switch 2')
    ]
    async_add_entities(switches)

  
  