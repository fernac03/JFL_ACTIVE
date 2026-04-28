"""Support for JFL alarm control panel."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JFLAlarmDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up JFL alarm control panel from a config entry."""
    coordinator: JFLAlarmDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([JFLAlarmControlPanel(coordinator, entry)])


class JFLAlarmControlPanel(CoordinatorEntity, AlarmControlPanelEntity):
    """Representation of a JFL alarm control panel."""

    def __init__(
        self,
        coordinator: JFLAlarmDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the alarm control panel."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_name = f"{coordinator.name} Alarm"
        self._attr_unique_id = f"{config_entry.entry_id}_alarm"

        self._attr_supported_features = (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
        )

        self._attr_code_format = CodeFormat.NUMBER
        self._attr_code_arm_required = False

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
            "configuration_url": f"http://{self.coordinator.host}:{self.coordinator.port}",
        }

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the state of the alarm."""
        if not self.coordinator.data:
            return None

        alarm_state = self.coordinator.data["alarm_state"]["state"]

        state_mapping = {
            "DISARMED": AlarmControlPanelState.DISARMED,
            "ARMED_HOME": AlarmControlPanelState.ARMED_HOME,
            "ARMED_STAY": AlarmControlPanelState.ARMED_HOME,
            "ARMED_AWAY": AlarmControlPanelState.ARMED_AWAY,
            "ALARM_SOUNDING": AlarmControlPanelState.TRIGGERED,
            "PENDING": AlarmControlPanelState.PENDING,
        }

        return state_mapping.get(alarm_state, AlarmControlPanelState.DISARMED)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}

        alarm_state = self.coordinator.data["alarm_state"]
        model_info = self.coordinator.data["model_info"]

        attributes = {
            "fire_alarm": alarm_state.get("fire_alarm", False),
            "medical_alarm": alarm_state.get("medical_alarm", False),
            "panic": alarm_state.get("panic", False),
            "eletrificador": alarm_state.get("eletrificador", False),
            "model": model_info.get("modelo", "Unknown"),
            "zones_count": model_info.get("numZonas", 0),
            "pgms_count": model_info.get("numPgms", 0),
            "partitions_count": model_info.get("numParticoes", 0),
        }

        zones = self.coordinator.data.get("zones", {})
        open_zones = [
            zone_data["name"]
            for zone_data in zones.values()
            if zone_data.get("state") == "open"
        ]

        if open_zones:
            attributes["open_zones"] = open_zones

        return attributes

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        success = await self.coordinator.async_disarm(code)
        if not success:
            _LOGGER.error("Failed to disarm alarm")

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        success = await self.coordinator.async_arm_home(code)
        if not success:
            _LOGGER.error("Failed to arm home")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        success = await self.coordinator.async_arm_away(code)
        if not success:
            _LOGGER.error("Failed to arm away")