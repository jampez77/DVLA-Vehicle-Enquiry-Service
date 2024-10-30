"""The DVLA integration."""

from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)
    # Registers update listener to update config entry when options are updated.
    unsub_options_update_listener = entry.add_update_listener(options_update_listener)

    # Use async_on_unload to register the listener without storing it in entry data
    entry.async_on_unload(unsub_options_update_listener)

    hass.data[DOMAIN][entry.entry_id] = hass_data

    # Forward the setup to each platform.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    entry_state = hass.config_entries.async_get_entry(config_entry.entry_id).state

    # Proceed only if the entry is in a valid state (loaded, etc.)
    if entry_state not in (
        ConfigEntryState.SETUP_IN_PROGRESS,
        ConfigEntryState.SETUP_RETRY,
    ):
        await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )

    # Remove config entry from domain.
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def handle_calendar_events(call: ServiceCall) -> None:
    """Handle calendar events."""


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the DVLA component from yaml configuration."""
    hass.services.async_register("calendar", "get_events", handle_calendar_events)
    hass.data.setdefault(DOMAIN, {})
    return True
