"""Sensor platform for the Aquilo integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from . import AquiloConfigEntry
from .const import CONF_EXCLUDED_SENSORS
from .coordinator import AquiloDataUpdateCoordinator
from .entity import AquiloEntity


def _parse_dt(value: Any) -> datetime | None:
    """Parse an ISO 8601 string (with offset) into a datetime, or None."""
    if not value:
        return None
    return dt_util.parse_datetime(str(value))


@dataclass(frozen=True, kw_only=True)
class AquiloSensorEntityDescription(SensorEntityDescription):
    """Describes an Aquilo sensor and how to read its value."""

    value_fn: Callable[[dict[str, Any]], StateType | datetime]


SENSOR_TYPES: tuple[AquiloSensorEntityDescription, ...] = (
    AquiloSensorEntityDescription(
        key="lvl",
        translation_key="lvl",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:waves",
        value_fn=lambda data: data.get("lvl"),
    ),
    AquiloSensorEntityDescription(
        key="pct",
        translation_key="pct",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-percent",
        value_fn=lambda data: data.get("pct"),
    ),
    AquiloSensorEntityDescription(
        key="bat",
        translation_key="bat",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("bat"),
    ),
    AquiloSensorEntityDescription(
        key="daysLeft",
        translation_key="days_left",
        native_unit_of_measurement=UnitOfTime.DAYS,
        icon="mdi:calendar-clock",
        value_fn=lambda data: data.get("daysLeft"),
    ),
    AquiloSensorEntityDescription(
        key="lvlToFull",
        translation_key="lvl_to_full",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        icon="mdi:arrow-collapse-up",
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.get("lvlToFull"),
    ),
    AquiloSensorEntityDescription(
        key="lstRead",
        translation_key="last_read",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        value_fn=lambda data: _parse_dt(data.get("lstRead")),
    ),
    AquiloSensorEntityDescription(
        key="lstEmpty",
        translation_key="last_emptied",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:delete-clock-outline",
        value_fn=lambda data: _parse_dt(data.get("lstEmpty")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AquiloConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aquilo sensors from a config entry."""
    coordinator = entry.runtime_data
    excluded = set(entry.options.get(CONF_EXCLUDED_SENSORS, []))

    entities = [
        AquiloSensor(coordinator, sensor_id, description)
        for sensor_id in coordinator.data
        if sensor_id not in excluded
        for description in SENSOR_TYPES
    ]
    async_add_entities(entities)


class AquiloSensor(AquiloEntity, SensorEntity):
    """A single Aquilo sensor reading for one device."""

    entity_description: AquiloSensorEntityDescription

    def __init__(
        self,
        coordinator: AquiloDataUpdateCoordinator,
        sensor_id: str,
        description: AquiloSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, sensor_id)
        self.entity_description = description
        self._attr_unique_id = f"{sensor_id}_{description.key}"

    @property
    def native_value(self) -> StateType | datetime:
        """Return the current value."""
        return self.entity_description.value_fn(self._sensor_data)
