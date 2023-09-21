"""DVLA sensor platform."""
from datetime import timedelta
import logging
from aiohttp import ClientError
from homeassistant.core import HomeAssistant, callback
from typing import Any
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .const import DOMAIN, CONF_REG_NUMBER
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from .coordinator import DVLACoordinator

_LOGGER = logging.getLogger(__name__)
# Time between updating data from GitHub
SCAN_INTERVAL = timedelta(minutes=10)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]
    # Update our config to include new repos and remove those that have been removed.
    if entry.options:
        config.update(entry.options)

    session = async_get_clientsession(hass)
    coordinator = DVLACoordinator(hass, session, entry.data)

    await coordinator.async_refresh()

    name = entry.data[CONF_REG_NUMBER]

    description = SensorEntityDescription(
        key=f"DVLA_{name}",
        name=name,
    )

    sensors = [DVLASensor(coordinator, name, description)]
    async_add_entities(sensors, update_before_add=True)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    _: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    session = async_get_clientsession(hass)
    coordinator = DVLACoordinator(hass, session, config)

    name = config[CONF_REG_NUMBER]

    description = SensorEntityDescription(
        key=f"DVLA_{name}",
        name=str(name).upper(),
    )

    sensors = [DVLASensor(coordinator, name, description)]
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
            identifiers={(DOMAIN, f"DVLA_{name}")},
            manufacturer="DVLA",
            name=name.upper(),
            configuration_url="https://github.com/jampez77/DVLA-Vehicle-Checker/",
        )
        self._attr_unique_id = f"dvla_{name}-{description.key}".lower()
        self.attrs: dict[str, Any] = {}
        self.entity_description = description
        self._state = None
        self._name = name.upper()
        self._available = True

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._attr_unique_id

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def icon(self) -> str:
        """Return a representative icon."""
        return "mdi:car"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        for key in self.coordinator.data:
            self.attrs[key] = self.coordinator.data[key]
        return self.attrs

    async def async_update(self) -> None:
        """Update the entity.

        Only used by the generic entity update service.
        """
        try:
            self._state = (
                str(self.coordinator.data["yearOfManufacture"])
                + " "
                + self.coordinator.data["make"]
                + " ("
                + self.coordinator.data["colour"]
                + ")"
            )
            self._available = True
        except (ClientError):
            self._available = False
            _LOGGER.exception(
                "Error retrieving data from DVLA for sensor %s", self.name
            )


class DVLAEntity(CoordinatorEntity, SensorEntity):
    """An entity using CoordinatorEntity."""

    def __init__(self, coordinator, idx):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=idx)
        self.idx = idx

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self.entity_description.attr_fn(self)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""

        self.async_write_ha_state()
