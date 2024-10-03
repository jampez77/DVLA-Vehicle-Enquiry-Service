"""DVLA binary sensor platform."""

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_REG_NUMBER, DOMAIN
from .coordinator import DVLACoordinator


@dataclass
class DVLABinarySensorEntityDescription(BinarySensorEntityDescription):
    """DVLA binary sensor description."""

    on_value: str | bool = True


SENSOR_TYPES = [
    DVLABinarySensorEntityDescription(
        key="taxStatus", name="Taxed", icon="mdi:car", on_value="Taxed"
    ),
    DVLABinarySensorEntityDescription(
        key="motStatus", name="MOT Valid", icon="mdi:car", on_value="Valid"
    ),
    DVLABinarySensorEntityDescription(
        key="markedForExport", name="Marked for Export", icon="mdi:export"
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
        DVLABinarySensor(coordinator, name, description)
        for description in SENSOR_TYPES
        if description.key in coordinator.data
    ]

    async_add_entities(sensors, update_before_add=True)


class DVLABinarySensor(CoordinatorEntity[DVLACoordinator], BinarySensorEntity):
    """Define an DVLA sensor."""

    def __init__(
        self,
        coordinator: DVLACoordinator,
        name: str,
        description: DVLABinarySensorEntityDescription,
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
        self._attr_unique_id = f"{DOMAIN}-{name}-{description.key}-binary".lower()
        self.entity_id = f"binary_sensor.{DOMAIN}_{name}_{description.key}".lower()
        self.attrs: dict[str, Any] = {}
        self.entity_description = description
        self._attr_is_on = False

    def update_from_coordinator(self):
        """Update sensor state and attributes from coordinator data."""

        value: str | bool = self.coordinator.data.get(self.entity_description.key, None)

        on_value = self.entity_description.on_value

        if type(on_value) is str:
            value = value.casefold() == on_value.casefold()

        self._attr_is_on = bool(value)

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
        return bool(self.coordinator.data)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._attr_is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Define entity attributes."""
        return self.attrs
