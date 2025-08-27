"""Support for JFL alarm switches (PGMs)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JFLAlarmDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up JFL switches from a config entry."""
    coordinator: JFLAlarmDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Wait for model info and PGMs to be available
    if coordinator.data and coordinator.data.get("pgms"):
        pgms = coordinator.data["pgms"]
        for pgm_id, pgm_data in pgms.items():
            entities.append(JFLPGMSwitch(coordinator, entry, pgm_id, pgm_data))
    
    async_add_entities(entities)


class JFLPGMSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a JFL PGM switch."""

    def __init__(
        self,
        coordinator: JFLAlarmDataUpdateCoordinator,
        config_entry: ConfigEntry,
        pgm_id: str,
        pgm_data: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._pgm_id = pgm_id
        self._pgm_number = pgm_data.get("pgm_number", 1)
        
        self._attr_name = f"{coordinator.name} {pgm_data.get('name', f'PGM {self._pgm_number}')}"
        self._attr_unique_id = f"{config_entry.entry_id}_{pgm_id}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        model_info = self.coordinator.model_info
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": self.coordinator.name,
            "manufacturer": "JFL Alarmes",
            "model": model_info.get("modelo", "Unknown"),
            "sw_version": "1.0",
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        if not self.coordinator.data:
            return None
        
        pgms = self.coordinator.data.get("pgms", {})
        pgm_data = pgms.get(self._pgm_id)
        
        if not pgm_data:
            return None
        
        return pgm_data.get("state") == "ON"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "pgm_number": self._pgm_number,
            "type": "toggle",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        success = await self.coordinator.async_pgm_on(self._pgm_number)
        if not success:
            _LOGGER.error("Failed to turn on PGM %s", self._pgm_number)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        success = await self.coordinator.async_pgm_off(self._pgm_number)
        if not success:
            _LOGGER.error("Failed to turn off PGM %s", self._pgm_number)
