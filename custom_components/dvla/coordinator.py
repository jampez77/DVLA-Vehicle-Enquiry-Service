"""DVLA Coordinator."""

from datetime import datetime, timedelta
import logging

from homeassistant.const import CONF_API_KEY, CONF_SCAN_INTERVAL, CONTENT_TYPE_JSON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_CALENDARS, CONF_REG_NUMBER, HOST

_LOGGER = logging.getLogger(__name__)


class DVLACoordinator(DataUpdateCoordinator):
    """Data coordinator."""

    def __init__(self, hass: HomeAssistant, session, data) -> None:
        """Initialize coordinator."""

        scan_interval = data.get(CONF_SCAN_INTERVAL, 21600)
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="DVLA",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=scan_interval),
        )
        self.session = session
        self.api_key = data[CONF_API_KEY]
        self.reg_number = str(data[CONF_REG_NUMBER]).upper()
        self._calendars = data[CONF_CALENDARS]
        self._hass = hass

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            resp = await self.session.request(
                method="POST",
                url=HOST,
                headers={
                    "Content-Type": CONTENT_TYPE_JSON,
                    "x-api-key": self.api_key,
                },
                json={"registrationNumber": self.reg_number},
            )
            body = await resp.json()
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except DVLAError as err:
            raise UpdateFailed(str(err)) from err
        except ValueError as err:
            err_str = str(err)

            if "Invalid authentication credentials" in err_str:
                raise InvalidAuth from err
            if "API rate limit exceeded." in err_str:
                raise APIRatelimitExceeded from err

            _LOGGER.exception("Unexpected exception")
            raise UnknownError from err

        if "errors" in body:
            error = body["errors"][0]
            raise UnknownError(
                f"Error setting up {self.reg_number}: {error['title']}({error['code']}) - {error['detail']}"
            )

        if "message" in body:
            raise UnknownError(f"Error setting up {self.reg_number}: {body['message']}")

        tax_date = body.get("taxDueDate")
        mot_date = body.get("motExpiryDate")
        for cal in self._calendars:
            await self.add_to_calendar(
                cal,
                tax_date,
                f"Tax - Due - {self.reg_number}",
                f"DVLA Reminder - Tax Due - {self.reg_number}",
            )
            await self.add_to_calendar(
                cal,
                mot_date,
                f"MOT - Expiry - {self.reg_number}",
                f"DVLA Reminder - Mot Expires - {self.reg_number}",
            )

        return body

    async def add_to_calendar(
        self, calendar: str, event_date: str, summary: str, description: str
    ):
        """Add an event to the calendar."""
        end_date = datetime.strptime(event_date, "%Y-%m-%d") + timedelta(days=1)
        service_data = {
            "entity_id": calendar,
            "start_date": event_date,
            "end_date": datetime.strftime(end_date, "%Y-%m-%d"),
            "summary": summary,
            "description": description,
        }
        if not await self._event_exists(service_data):
            await self.create_event(service_data)

    async def _event_exists(self, service_data) -> bool:
        """Fetch the created event by matching with details in service_data."""
        entity_id = service_data.get("entity_id")
        start_date_time = f"{service_data.get('start_date')} 00:00:00"
        events = await self._hass.services.async_call(
            "calendar",
            "get_events",
            {
                "entity_id": entity_id,
                "start_date_time": start_date_time,
                "duration": {"days": 1},
            },
            return_response=True,
            blocking=True,
        )
        if (
            events
            and (event_list := events.get(entity_id))
            and isinstance(event_list, dict)
        ):
            for event in event_list.get("events", {}):
                if (
                    event["summary"] == service_data["summary"]
                    and f"{event['description']}" == f"{service_data['description']}"
                ):
                    return True

        return False

    async def create_event(self, service_data):
        """Create calendar event."""
        await self._hass.services.async_call(
            "calendar",
            "create_event",
            service_data,
            blocking=True,
        )


class DVLAError(HomeAssistantError):
    """Base error."""


class InvalidAuth(DVLAError):
    """Raised when invalid authentication credentials are provided."""


class APIRatelimitExceeded(DVLAError):
    """Raised when the API rate limit is exceeded."""


class UnknownError(DVLAError):
    """Raised when an unknown error occurs."""
