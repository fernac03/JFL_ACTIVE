"""The JFL Alarm integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_NAME,
    Platform,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_KEEP_ALIVE_INTERVAL,
    CONF_ENABLE_KEEP_ALIVE,
    CONF_GET_STATE_INTERVAL,
    CONF_ENABLE_GET_STATE,
    DEFAULT_PORT,
    DEFAULT_KEEP_ALIVE_INTERVAL,
    DEFAULT_GET_STATE_INTERVAL,
)
from .coordinator import JFLAlarmDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(CONF_NAME): cv.string,
                vol.Optional(
                    CONF_KEEP_ALIVE_INTERVAL, default=DEFAULT_KEEP_ALIVE_INTERVAL
                ): cv.positive_int,
                vol.Optional(CONF_ENABLE_KEEP_ALIVE, default=True): cv.boolean,
                vol.Optional(
                    CONF_GET_STATE_INTERVAL, default=DEFAULT_GET_STATE_INTERVAL
                ): cv.positive_int,
                vol.Optional(CONF_ENABLE_GET_STATE, default=True): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config: ConfigType) -> bool:
    """Set up the JFL Alarm integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass, entry: ConfigEntry) -> bool:
    """Set up JFL Alarm from a config entry."""
    coordinator = JFLAlarmDataUpdateCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    return unload_ok