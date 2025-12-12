"""The DVLA integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_API_KEY, CONTENT_TYPE_JSON, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_API_KEY,
    ATTR_REG_NUMBER,
    DOMAIN,
    HOST,
    SERVICE_LOOKUP,
)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

LOOKUP_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_REG_NUMBER): cv.string,
        vol.Optional(ATTR_API_KEY): cv.string,
    }
)

_LOGGER = logging.getLogger(__name__)


async def _async_single_lookup(
    hass: HomeAssistant, api_key: str, reg_number: str
) -> Any:
    """Perform a one-off DVLA lookup."""

    session = async_get_clientsession(hass)

    try:
        resp = await session.post(
            HOST,
            headers={
                "Content-Type": CONTENT_TYPE_JSON,
                "x-api-key": api_key,
            },
            json={"registrationNumber": str(reg_number).upper()},
        )
        body = await resp.json()
    except ValueError as err:
        _LOGGER.exception("Failed to parse DVLA response")
        raise HomeAssistantError("Invalid response from DVLA API") from err

    if "errors" in body:
        error = body["errors"][0]
        raise HomeAssistantError(
            f"{error.get('title')}({error.get('code')}): {error.get('detail')}"
        )

    if "message" in body:
        raise HomeAssistantError(body["message"])

    if resp.status >= 400:
        raise HomeAssistantError(
            f"DVLA lookup failed with status {resp.status}: {body}"
        )

    return body


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the DVLA integration."""

    async def handle_lookup(call: ServiceCall):
        """Handle dvla.lookup service."""

        reg_number = call.data[ATTR_REG_NUMBER]
        api_key = call.data.get(ATTR_API_KEY)

        if api_key is None:
            entries = hass.config_entries.async_entries(DOMAIN)
            api_key = next(
                (
                    entry.data.get(CONF_API_KEY)
                    for entry in entries
                    if entry.state == ConfigEntryState.LOADED
                    and entry.data.get(CONF_API_KEY)
                ),
                None,
            )

            if api_key is None:
                api_key = next(
                    (
                        entry.data.get(CONF_API_KEY)
                        for entry in entries
                        if entry.data.get(CONF_API_KEY)
                    ),
                    None,
                )

        if not api_key:
            raise HomeAssistantError(
                "DVLA API key is required; provide api_key or configure the integration."
            )

        return await _async_single_lookup(hass, api_key, reg_number)

    hass.services.async_register(
        DOMAIN,
        SERVICE_LOOKUP,
        handle_lookup,
        schema=LOOKUP_SCHEMA,
        supports_response=True,
    )

    return True


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
