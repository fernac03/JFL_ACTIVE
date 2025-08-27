"""Support for JFL alarm binary sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up JFL binary sensors from a config entry."""
    coordinator: JFLAlarmDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Wait for model info to be available
    if coordinator.data and coordinator.data.get("zones"):
        zones = coordinator.data["zones"]
        for zone_id, zone_data in zones.items():
            entities.append(JFLZoneBinarySensor(coordinator, entry, zone_id, zone_data))
    
    # Add system binary sensors
    entities.extend([
        JFLSystemBinarySensor(coordinator, entry, "fire_alarm", "Fire Alarm", BinarySensorDeviceClass.FIRE),
        JFLSystemBinarySensor(coordinator, entry, "medical_alarm", "Medical Alarm", BinarySensorDeviceClass.SAFETY),
        JFLSystemBinarySensor(coordinator, entry, "panic", "Panic", BinarySensorDeviceClass.SAFETY),
        JFLSystemBinarySensor(coordinator, entry, "eletrificador", "Eletrificador", BinarySensorDeviceClass.POWER),
    ])
    
    async_add_entities(entities)


class JFLZoneBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a JFL zone binary sensor."""

    def __init__(
        self,
        coordinator: JFLAlarmDataUpdateCoordinator,
        config_entry: ConfigEntry,
        zone_id: str,
        zone_data: dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._zone_id = zone_id
        self._zone_number = zone_data.get("zone_number", 1)
        
        self._attr_name = f"{coordinator.name} {zone_data.get('name', f'Zone {self._zone_number}')}"
        self._attr_unique_id = f"{config_entry.entry_id}_{zone_id}"
        self._attr_device_class = BinarySensorDeviceClass.DOOR  # Default, can be customized

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
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None
        
        zones = self.coordinator.data.get("zones", {})
        zone_data = zones.get(self._zone_id)
        
        if not zone_data:
            return None
        
        return zone_data.get("state") == "open"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        zones = self.coordinator.data.get("zones", {})
        zone_data = zones.get(self._zone_id, {})
        
        return {
            "zone_number": self._zone_number,
            "status": zone_data.get("status", "unknown"),
            "raw_status": zone_data.get("raw_status"),
        }


class JFLSystemBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a JFL system binary sensor."""

    def __init__(
        self,
        coordinator: JFLAlarmDataUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_key: str,
        sensor_name: str,
        device_class: BinarySensorDeviceClass,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._sensor_key = sensor_key
        
        self._attr_name = f"{coordinator.name} {sensor_name}"
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_key}"
        self._attr_device_class = device_class

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
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None
        
        alarm_state = self.coordinator.data.get("alarm_state", {})
        return alarm_state.get(self._sensor_key, False)
