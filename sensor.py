"""Support for JFL alarm sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JFLAlarmDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up JFL sensors from a config entry."""
    coordinator: JFLAlarmDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Battery sensor
    entities.append(JFLBatterySensor(coordinator, entry))
    
    # Partition sensors
    if coordinator.data and coordinator.data.get("partitions"):
        partitions = coordinator.data["partitions"]
        for partition_id, partition_data in partitions.items():
            entities.append(JFLPartitionSensor(coordinator, entry, partition_id, partition_data))
    
    async_add_entities(entities)


class JFLBatterySensor(CoordinatorEntity, SensorEntity):
    """Representation of a JFL battery sensor."""

    def __init__(
        self,
        coordinator: JFLAlarmDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        
        self._attr_name = f"{coordinator.name} Battery"
        self._attr_unique_id = f"{config_entry.entry_id}_battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

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
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        sensors = self.coordinator.data.get("sensors", {})
        battery_data = sensors.get("bateria")
        
        if not battery_data:
            return None
        
        return battery_data.get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}
        
        sensors = self.coordinator.data.get("sensors", {})
        battery_data = sensors.get("bateria", {})
        
        return {
            "description": battery_data.get("description", "Unknown"),
            "raw_value": battery_data.get("raw_value"),
        }


class JFLPartitionSensor(CoordinatorEntity, SensorEntity):
    """Representation of a JFL partition sensor."""

    def __init__(
        self,
        coordinator: JFLAlarmDataUpdateCoordinator,
        config_entry: ConfigEntry,
        partition_id: str,
        partition_data: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._partition_id = partition_id
        self._partition_number = partition_data.get("partition_number", 1)
        
        self._attr_name = f"{coordinator.name} {partition_data.get('name', f'Partition {self._partition_number}')}"
        self._attr_unique_id = f"{config_entry.entry_id}_{partition_id}"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["DISARMED", "ARMED_HOME", "ARMED_AWAY", "ALARM_SOUNDING", "PENDING"]

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
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        partitions = self.coordinator.data.get("partitions", {})
        partition_data = partitions.get(self._partition_id)
        
        if not partition_data:
            return None
        
        return partition_data.get("state", "DISARMED")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "partition_number": self._partition_number,
        }
