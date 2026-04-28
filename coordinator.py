"""Data update coordinator for JFL Alarm."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_KEEP_ALIVE_INTERVAL,
    CONF_ENABLE_KEEP_ALIVE,
    CONF_GET_STATE_INTERVAL,
    CONF_ENABLE_GET_STATE,
    ALARM_COMMANDS,
    JFL_MODELS,
    EVENT_CODES,
    ZONE_STATUS_MAP,
)
from .jfl_protocol import JFLProtocol

_LOGGER = logging.getLogger(__name__)


class JFLAlarmDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the JFL Alarm system."""

    def __init__(self, hass, config_entry: ConfigEntry) -> None:
        """Initialize."""
        self.config_entry = config_entry
        self.host = config_entry.data[CONF_HOST]
        self.port = config_entry.data[CONF_PORT]
        self.name = config_entry.data.get(CONF_NAME, "JFL Alarm")
        
        self.keep_alive_interval = config_entry.data.get(CONF_KEEP_ALIVE_INTERVAL, 30000) / 1000
        self.enable_keep_alive = config_entry.data.get(CONF_ENABLE_KEEP_ALIVE, True)
        self.get_state_interval = config_entry.data.get(CONF_GET_STATE_INTERVAL, 5000) / 1000
        self.enable_get_state = config_entry.data.get(CONF_ENABLE_GET_STATE, True)
        
        # Initialize protocol handler
        self.protocol = JFLProtocol(self.host, self.port)
        
        # Current state
        self.current_state = {
            "armed_away": False,
            "armed_night": False,
            "armed_home": False,
            "alarm_sounding": False,
            "fire_alarm": False,
            "medical_alarm": False,
            "panic": False,
            "eletrificador": False,
            "state": "DISARMED",
        }
        
        # Device info
        self.model_info = {
            "modelo": "Unknown",
            "temEletrificador": False,
            "numZonas": 0,
            "numPgms": 0,
            "numParticoes": 0,
        }
        
        # Zones, sensors, and PGMs
        self.zonas = {}
        self.sensors = {}
        self.pgms = {}
        self.particoes = {}
        
        # Tasks
        self._keep_alive_task = None
        self._get_state_task = None
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self._async_update_data,
            update_interval=None,  # We'll handle updates via TCP events
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh and setup."""
        # Start the protocol connection
        await self.protocol.connect()
        
        # Set up event handlers
        self.protocol.set_event_callback(self._handle_alarm_event)
        self.protocol.set_model_callback(self._handle_model_info)
        self.protocol.set_status_callback(self._handle_status_update)
        
        # Start background tasks
        if self.enable_keep_alive:
            self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
        
        if self.enable_get_state:
            self._get_state_task = asyncio.create_task(self._get_state_loop())
        
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        return {
            "alarm_state": self.current_state,
            "model_info": self.model_info,
            "zones": self.zonas,
            "sensors": self.sensors,
            "pgms": self.pgms,
            "partitions": self.particoes,
        }

    async def _keep_alive_loop(self) -> None:
        """Send keep alive messages periodically."""
        while True:
            try:
                await asyncio.sleep(self.keep_alive_interval)
                await self.protocol.send_keep_alive()
                _LOGGER.debug("Keep alive sent")
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Error in keep alive loop: %s", err)
                await asyncio.sleep(5)  # Wait before retrying

    async def _get_state_loop(self) -> None:
        """Request state periodically."""
        while True:
            try:
                await asyncio.sleep(self.get_state_interval)
                await self.protocol.send_get_state()
                _LOGGER.debug("Get state request sent")
            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Error in get state loop: %s", err)
                await asyncio.sleep(5)  # Wait before retrying

    def _handle_alarm_event(self, event_data: dict[str, Any]) -> None:
        """Handle alarm events."""
        _LOGGER.info("Alarm event received: %s", event_data)
        
        # Update current state based on event
        if "state" in event_data:
            self.current_state.update({
                "armed_away": event_data.get("armed_away", False),
                "armed_night": event_data.get("armed_night", False),
                "armed_home": event_data.get("armed_home", False),
                "alarm_sounding": event_data.get("alarm_sounding", False),
                "fire_alarm": event_data.get("fire_alarm", False),
                "medical_alarm": event_data.get("medical_alarm", False),
                "panic": event_data.get("panic", False),
                "eletrificador": event_data.get("eletrificador", False),
                "state": event_data.get("state", "DISARMED"),
            })
        
        # Trigger update
        self.async_set_updated_data(self._build_data())

    def _handle_model_info(self, model_data: dict[str, Any]) -> None:
        """Handle model information."""
        _LOGGER.info("Model info received: %s", model_data)
        self.model_info.update(model_data)
        
        # Initialize zones, PGMs, and partitions based on model
        self._initialize_entities()
        
        # Trigger update
        self.async_set_updated_data(self._build_data())

    def _handle_status_update(self, status_data: dict[str, Any]) -> None:
        """Handle status updates."""
        _LOGGER.debug("Status update received")
        
        # Update zones
        if "zones" in status_data:
            self.zonas.update(status_data["zones"])
        
        # Update sensors
        if "sensors" in status_data:
            self.sensors.update(status_data["sensors"])
        
        # Update PGMs
        if "pgms" in status_data:
            self.pgms.update(status_data["pgms"])
        
        # Trigger update
        self.async_set_updated_data(self._build_data())

    def _initialize_entities(self) -> None:
        """Initialize zones, PGMs, and partitions based on model."""
        num_zonas = self.model_info.get("numZonas", 0)
        num_pgms = self.model_info.get("numPgms", 0)
        num_particoes = self.model_info.get("numParticoes", 0)
        
        # Initialize zones
        for i in range(num_zonas):
            zone_id = f"zona_{i + 1}"
            self.zonas[zone_id] = {
                "name": f"Zona {i + 1}",
                "state": "closed",
                "zone_number": i + 1,
            }
        
        # Initialize PGMs
        for i in range(num_pgms):
            pgm_id = f"pgm_{i + 1}"
            self.pgms[pgm_id] = {
                "name": f"PGM {i + 1}",
                "state": "OFF",
                "type": "toggle",
                "pgm_number": i + 1,
            }
        
        # Initialize partitions
        for i in range(num_particoes):
            partition_id = f"particao_{i + 1}"
            self.particoes[partition_id] = {
                "name": f"Partição {i + 1}",
                "state": "DISARMED",
                "partition_number": i + 1,
            }
        
        # Initialize battery sensor
        self.sensors["bateria"] = {
            "name": "Bateria",
            "state": None,
            "device_class": "battery",
        }

    def _build_data(self) -> dict[str, Any]:
        """Build the data dictionary."""
        return {
            "alarm_state": self.current_state,
            "model_info": self.model_info,
            "zones": self.zonas,
            "sensors": self.sensors,
            "pgms": self.pgms,
            "partitions": self.particoes,
        }

    async def async_arm_away(self, code: str | None = None) -> bool:
        """Arm the alarm in away mode."""
        try:
            await self.protocol.send_command(ALARM_COMMANDS["ARM_AWAY"])
            return True
        except Exception as err:
            _LOGGER.error("Failed to arm away: %s", err)
            return False

    async def async_arm_home(self, code: str | None = None) -> bool:
        """Arm the alarm in home mode."""
        try:
            await self.protocol.send_command(ALARM_COMMANDS["ARM_STAY"])
            return True
        except Exception as err:
            _LOGGER.error("Failed to arm home: %s", err)
            return False

    async def async_disarm(self, code: str | None = None) -> bool:
        """Disarm the alarm."""
        try:
            await self.protocol.send_command(ALARM_COMMANDS["DISARM"])
            return True
        except Exception as err:
            _LOGGER.error("Failed to disarm: %s", err)
            return False

    async def async_pgm_on(self, pgm_number: int) -> bool:
        """Turn on a PGM."""
        try:
            if pgm_number < 1 or pgm_number > 16:
                raise ValueError(f"Invalid PGM number: {pgm_number}")
            
            if pgm_number > self.model_info.get("numPgms", 0):
                raise ValueError(f"PGM {pgm_number} not available on this model")
            
            command = ALARM_COMMANDS["PGM_ON"] + [pgm_number]
            await self.protocol.send_command(command)
            return True
        except Exception as err:
            _LOGGER.error("Failed to turn on PGM %s: %s", pgm_number, err)
            return False

    async def async_pgm_off(self, pgm_number: int) -> bool:
        """Turn off a PGM."""
        try:
            if pgm_number < 1 or pgm_number > 16:
                raise ValueError(f"Invalid PGM number: {pgm_number}")
            
            if pgm_number > self.model_info.get("numPgms", 0):
                raise ValueError(f"PGM {pgm_number} not available on this model")
            
            command = ALARM_COMMANDS["PGM_OFF"] + [pgm_number]
            await self.protocol.send_command(command)
            return True
        except Exception as err:
            _LOGGER.error("Failed to turn off PGM %s: %s", pgm_number, err)
            return False

    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        # Cancel background tasks
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            try:
                await self._keep_alive_task
            except asyncio.CancelledError:
                pass
        
        if self._get_state_task:
            self._get_state_task.cancel()
            try:
                await self._get_state_task
            except asyncio.CancelledError:
                pass
        
        # Close protocol connection
        await self.protocol.disconnect()
