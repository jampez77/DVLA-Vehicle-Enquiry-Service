"""DVLA sensor platform."""

from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_REG_NUMBER, DOMAIN
from .coordinator import DVLACoordinator

SENSOR_TYPES = [
    SensorEntityDescription(
        key="registrationNumber", name="Registration Number", icon="mdi:car"
    ),
    SensorEntityDescription(key="taxStatus", name="Tax Status", icon="mdi:car"),
    SensorEntityDescription(
        key="taxDueDate",
        name="Tax Due Date",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.DATE,
    ),
    SensorEntityDescription(key="motStatus", name="MOT Status", icon="mdi:car"),
    SensorEntityDescription(key="make", name="Make", icon="mdi:car"),
    SensorEntityDescription(
        key="yearOfManufacture", name="Year of Manufacture", icon="mdi:car"
    ),
    SensorEntityDescription(
        key="engineCapacity", name="Engine Capacity", icon="mdi:engine"
    ),
    SensorEntityDescription(
        key="co2Emissions", name="CO2 Emissions", icon="mdi:engine"
    ),
    SensorEntityDescription(key="fuelType", name="Fuel Type", icon="mdi:engine"),
    SensorEntityDescription(key="colour", name="Colour", icon="mdi:spray"),
    SensorEntityDescription(key="typeApproval", name="Type Approval", icon="mdi:car"),
    SensorEntityDescription(
        key="revenueWeight",
        name="Revenue Weight",
        icon="mdi:weight",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
    ),
    SensorEntityDescription(
        key="dateOfLastV5CIssued",
        name="Date of Last V5C Issued",
        icon="mdi:calendar",
        device_class=SensorDeviceClass.DATE,
    ),
    SensorEntityDescription(
        key="motExpiryDate",
        name="MOT Expiry Date",
        icon="mdi:calendar-check",
        device_class=SensorDeviceClass.DATE,
    ),
    SensorEntityDescription(key="wheelplan", name="Wheelplan", icon="mdi:car"),
    SensorEntityDescription(
        key="monthOfFirstRegistration",
        name="Month of First Registration",
        icon="mdi:calendar",
    ),
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

    session = async_get_clientsession(hass)
    coordinator = DVLACoordinator(hass, session, entry.data)

    await coordinator.async_refresh()

    name = entry.data[CONF_REG_NUMBER]

    sensors = [
        DVLASensor(coordinator, name, description)
        for description in SENSOR_TYPES
        if description.key in coordinator.data
        # Special case: allow motExpiryDate sensor even if key is missing,
        # so we can calculate the fallback date.
        or description.key == "motExpiryDate"
    ]

    async_add_entities(sensors, update_before_add=True)


class DVLASensor(CoordinatorEntity[DVLACoordinator], SensorEntity):
    """Define an DVLA sensor."""

    def __init__(
        self,
        coordinator: DVLACoordinator,
        name: str,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{name}")},
            manufacturer=DOMAIN.upper(),
            model=coordinator.data.get("make"),
            name=name.upper(),
            configuration_url="https://github.com/jampez77/DVLA-Vehicle-Checker/",
        )
        self._attr_unique_id = f"{DOMAIN}-{name}-{description.key}".lower()
        self.entity_id = f"sensor.{DOMAIN}_{name}_{description.key}".lower()
        self.attrs: dict[str, Any] = {}
        self.entity_description = description
        self._state = None

    def update_from_coordinator(self):
        """Update sensor state and attributes from coordinator data."""
        self._state = self.coordinator.data.get(self.entity_description.key)

        # --- Handle missing MOT Date ---
        if self.entity_description.key == "motExpiryDate" and not self._state:
            # If MOT date is missing, calculate 3 years from first registration month
            reg_month_str = self.coordinator.data.get("monthOfFirstRegistration")
            if reg_month_str:
                try:
                    # Parse "YYYY-MM"
                    year_str, month_str = reg_month_str.split("-")
                    reg_year = int(year_str)
                    reg_month = int(month_str)
                    
                    # Calculate: 1st of the month + 3 years
                    # We output as string so the standard logic below picks it up
                    calculated_date = date(reg_year + 3, reg_month, 1)
                    self._state = calculated_date.isoformat()
                except (ValueError, IndexError):
                    # Keep as None if parsing fails
                    pass
        # ---------------------------------------------

        if self._state is not None:
            if (
                self._state
                and self.entity_description.device_class == SensorDeviceClass.DATE
            ):
                try:
                    # Try to parse the string into a date object
                    self._state = date.fromisoformat(self._state)
                except ValueError:
                    self._state = None

            for key in self.coordinator.data:
                self.attrs[key] = self.coordinator.data[key]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.update_from_coordinator()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle adding to Home Assistant."""
        await super().async_added_to_hass()
        await self.async_update()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Ensure entity is available even if specific key is missing but we have coordinator data
        return bool(self.coordinator.data)

    @property
    def native_value(self) -> str | date | None:
        """Native value."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Define entity attributes."""
        return self.attrs
