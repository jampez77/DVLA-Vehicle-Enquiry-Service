"""DVLA sensor platform."""

from datetime import date, datetime
import hashlib
import json
import uuid

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CALENDARS, CONF_REG_NUMBER, DOMAIN
from .coordinator import DVLACoordinator
from .sensor import SENSOR_TYPES

DATE_SENSOR_TYPES = [
    st for st in SENSOR_TYPES if st.device_class == SensorDeviceClass.DATE
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]
    # Update our config to include new repos and remove those that have been removed.
    if entry.options:
        config.update(entry.options)

    reg_number = entry.data[CONF_REG_NUMBER]

    calendars = entry.data[CONF_CALENDARS]

    session = async_get_clientsession(hass)
    coordinator = DVLACoordinator(hass, session, entry.data)

    await coordinator.async_refresh()

    sensors = [DVLACalendarSensor(coordinator, reg_number)]

    for calendar in calendars:
        if calendar != "None":
            for sensor in sensors:
                events = sensor.get_events(datetime.today(), reg_number)
                for event in events:
                    await add_to_calendar(hass, calendar, event, entry)

    if "None" in calendars:
        async_add_entities(sensors, update_before_add=True)


async def create_event(hass: HomeAssistant, service_data):
    """Create calendar event."""
    try:
        await hass.services.async_call(
            "calendar",
            "create_event",
            service_data,
            blocking=True,
            return_response=True,
        )
    except (ServiceValidationError, HomeAssistantError):
        await hass.services.async_call(
            "calendar",
            "create_event",
            service_data,
            blocking=True,
        )


class DateTimeEncoder(json.JSONEncoder):
    """Encode date time object."""

    def default(self, o):
        """Encode date time object."""
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)


def generate_uuid_from_json(json_obj):
    """Generate a UUID from a JSON object."""

    json_string = json.dumps(json_obj, cls=DateTimeEncoder, sort_keys=True)

    sha1_hash = hashlib.sha1(json_string.encode("utf-8")).digest()

    return str(uuid.UUID(bytes=sha1_hash[:16]))


async def get_event_uid(hass: HomeAssistant, service_data) -> str | None:
    """Fetch the created event by matching with details in service_data."""
    entity_id = service_data.get("entity_id")
    start_time = service_data.get("start_date")
    end_time = service_data.get("end_date")

    try:
        events = await hass.services.async_call(
            "calendar",
            "get_events",
            {
                "entity_id": entity_id,
                "start_date_time": f"{start_time}T00:00:00+0000",
                "end_date_time": f"{end_time}T00:00:00+0000",
            },
            return_response=True,
            blocking=True,
        )
    except (ServiceValidationError, HomeAssistantError):
        events = None

    if events is not None and entity_id in events:
        for event in events[entity_id].get("events"):
            if (
                event["summary"] == service_data["summary"]
                and f"{event["description"]}" == f"{service_data["description"]}"
                and f"{event["location"]}" == f"{service_data["location"]}"
            ):
                return generate_uuid_from_json(service_data)

    return None


async def add_to_calendar(
    hass: HomeAssistant, calendar: str, event: CalendarEvent, entry: ConfigEntry
):
    """Add an event to the calendar."""

    service_data = {
        "entity_id": calendar,
        "start_date": event.start,
        "end_date": event.end,
        "summary": event.summary,
        "description": f"{event.description}",
        "location": f"{event.location}",
    }

    uid = await get_event_uid(hass, service_data)

    uids = entry.data.get("uids", [])

    if uid not in uids:
        await create_event(hass, service_data)

        created_event_uid = await get_event_uid(hass, service_data)

        if created_event_uid is not None and created_event_uid not in uids:
            uids.append(created_event_uid)

    if uids != entry.data.get("uids", []):
        updated_data = entry.data.copy()
        updated_data["uids"] = uids
        hass.config_entries.async_update_entry(entry, data=updated_data)


class DVLACalendarSensor(CoordinatorEntity[DVLACoordinator], CalendarEntity):
    """Define an DVLA sensor."""

    def __init__(
        self,
        coordinator: DVLACoordinator,
        reg_number: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{reg_number}")},
            manufacturer=DOMAIN.upper(),
            model=coordinator.data.get("make"),
            name=reg_number.upper(),
            configuration_url="https://github.com/jampez77/DVLA-Vehicle-Checker/",
        )
        self._attr_unique_id = f"{DOMAIN}-{reg_number}-calendar".lower()
        self._attr_name = f"{DOMAIN} - {reg_number}".upper()
        self.reg_number = reg_number

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self.coordinator.data)

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        events = self.get_events(datetime.today(), self.reg_number)
        return sorted(events, key=lambda c: c.start)[0]

    def get_events(self, start_date: datetime, reg_number: str) -> list[CalendarEvent]:
        """Return calendar events."""
        events = []
        for date_sensor_type in DATE_SENSOR_TYPES:
            raw_value = self.coordinator.data.get(date_sensor_type.key)
            if not raw_value:
                continue
            value = date.fromisoformat(raw_value)
            if value >= start_date.date():
                event_name = date_sensor_type.name.replace(" Date", f" - {reg_number}")
                events.append(CalendarEvent(value, value, event_name))
        return events

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        return [
            event
            for event in self.get_events(start_date, self.reg_number)
            if event.start <= end_date.date()
        ]
