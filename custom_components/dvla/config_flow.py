"""Config flow for DVLA integration."""

from __future__ import annotations

from collections import OrderedDict
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.calendar import CalendarEntityFeature
from homeassistant.const import CONF_API_KEY, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import CONF_CALENDARS, CONF_REG_NUMBER, DOMAIN
from .coordinator import DVLACoordinator

_LOGGER = logging.getLogger(__name__)


async def _get_calendar_entities(hass: HomeAssistant) -> list[str]:
    """Retrieve calendar entities."""
    entity_registry = er.async_get(hass)
    calendar_entities = {}
    for entity_id, entity in entity_registry.entities.items():
        if entity_id.startswith("calendar."):
            calendar_entity = hass.states.get(entity_id)
            if calendar_entity:
                supported_features = calendar_entity.attributes.get(
                    "supported_features", 0
                )

                supports_create_event = (
                    supported_features & CalendarEntityFeature.CREATE_EVENT
                )

                if supports_create_event:
                    calendar_name = entity.original_name or entity_id
                    calendar_entities[entity_id] = calendar_name

    calendar_entities["None"] = "Create a new calendar"
    return calendar_entities


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    coordinator = DVLACoordinator(hass, session, data)

    await coordinator.async_refresh()

    if coordinator.last_exception is not None:
        raise InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": str(data[CONF_REG_NUMBER]).upper()}


class DVLAFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for DVLA."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config = OrderedDict()
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""

        calendar_entities = await _get_calendar_entities(self.hass)

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.data.get(CONF_SCAN_INTERVAL, 21600),
                ): cv.positive_int,
                vol.Required(
                    CONF_CALENDARS,
                    default=self.config_entry.data.get(CONF_CALENDARS, []),
                ): cv.multi_select(calendar_entities),
            }
        )

        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=user_input, options=self.config_entry.options
            )
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DVLA."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}

        calendar_entities = await _get_calendar_entities(self.hass)

        user_input = user_input or {}

        STEP_USER_DATA_SCHEMA = vol.Schema(
            {
                vol.Required(
                    CONF_API_KEY, default=user_input.get(CONF_API_KEY, "")
                ): cv.string,
                vol.Required(
                    CONF_REG_NUMBER, default=user_input.get(CONF_REG_NUMBER, "")
                ): cv.string,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=user_input.get(CONF_SCAN_INTERVAL, 21600),
                ): cv.positive_int,
                vol.Required(
                    CONF_CALENDARS, default=user_input.get(CONF_CALENDARS, [])
                ): cv.multi_select(calendar_entities),
            }
        )
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        if user_input:
            entries = self.hass.config_entries.async_entries(DOMAIN)

            if any(
                entry.data.get(CONF_REG_NUMBER) == user_input.get(CONF_REG_NUMBER)
                for entry in entries
            ):
                errors["base"] = "vehicle_exists"

            if not user_input.get(CONF_CALENDARS):
                errors["base"] = "no_calendar_selected"

            if not errors:
                try:
                    info = await validate_input(self.hass, user_input)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return DVLAFlowHandler(config_entry)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
