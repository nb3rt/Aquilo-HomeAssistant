"""Binary sensor platform for the Aquilo integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import AquiloConfigEntry
from .const import (
    CONF_EXCLUDED_SENSORS,
    CONF_OVERFLOW_PCT,
    CONF_STALE_HOURS,
    DEFAULT_OVERFLOW_PCT,
    DEFAULT_STALE_HOURS,
)
from .coordinator import AquiloDataUpdateCoordinator
from .entity import AquiloEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AquiloConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aquilo binary sensors from a config entry."""
    coordinator = entry.runtime_data
    excluded = set(entry.options.get(CONF_EXCLUDED_SENSORS, []))
    stale_hours = entry.options.get(CONF_STALE_HOURS, DEFAULT_STALE_HOURS)
    overflow_pct = entry.options.get(CONF_OVERFLOW_PCT, DEFAULT_OVERFLOW_PCT)

    entities: list[BinarySensorEntity] = []
    for sensor_id in coordinator.data:
        if sensor_id in excluded:
            continue
        entities.append(AquiloStaleDataSensor(coordinator, sensor_id, stale_hours))
        entities.append(
            AquiloOverflowRiskSensor(coordinator, sensor_id, overflow_pct)
        )
    async_add_entities(entities)


class AquiloStaleDataSensor(AquiloEntity, BinarySensorEntity):
    """On when the device has not reported a reading for too long.

    The gateway keeps serving the last reading it got, so a sensor with a flat
    battery or a lost radio link looks healthy in every other entity.
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "stale_data"

    def __init__(
        self,
        coordinator: AquiloDataUpdateCoordinator,
        sensor_id: str,
        stale_hours: int,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, sensor_id)
        self._stale_hours = stale_hours
        self._attr_unique_id = f"{sensor_id}_stale_data"

    @property
    def _last_read(self) -> datetime | None:
        value = self._sensor_data.get("lstRead")
        return dt_util.parse_datetime(str(value)) if value else None

    @property
    def is_on(self) -> bool | None:
        """Return True if the last reading is older than the threshold."""
        if (last_read := self._last_read) is None:
            return None
        age = dt_util.utcnow() - dt_util.as_utc(last_read)
        return age.total_seconds() > self._stale_hours * 3600

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the age of the last reading."""
        if (last_read := self._last_read) is None:
            return {}
        age = dt_util.utcnow() - dt_util.as_utc(last_read)
        return {"hours_since_last_read": round(age.total_seconds() / 3600, 1)}


class AquiloOverflowRiskSensor(AquiloEntity, BinarySensorEntity):
    """On when the fill level reaches the configured threshold."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "overflow_risk"

    def __init__(
        self,
        coordinator: AquiloDataUpdateCoordinator,
        sensor_id: str,
        overflow_pct: int,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, sensor_id)
        self._overflow_pct = overflow_pct
        self._attr_unique_id = f"{sensor_id}_overflow_risk"

    @property
    def is_on(self) -> bool | None:
        """Return True if the tank is filled at or above the threshold."""
        pct = self._sensor_data.get("pct")
        if pct is None:
            return None
        return pct >= self._overflow_pct
