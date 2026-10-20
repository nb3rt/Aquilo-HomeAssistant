"""Base entity for the Aquilo integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import AquiloDataUpdateCoordinator


class AquiloEntity(CoordinatorEntity[AquiloDataUpdateCoordinator]):
    """An entity tied to one sensor id in the coordinator data."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: AquiloDataUpdateCoordinator, sensor_id: str
    ) -> None:
        """Initialize the entity and its device."""
        super().__init__(coordinator)
        self._sensor_id = sensor_id

        name = self._sensor_data.get("name") or f"Aquilo {sensor_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, sensor_id)},
            name=name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url="https://www.aquilo.pl",
        )

    @property
    def _sensor_data(self) -> dict[str, Any]:
        """Return this device's slice of the coordinator data."""
        return self.coordinator.data.get(self._sensor_id, {})

    @property
    def available(self) -> bool:
        """Return True if the device is still present in the latest payload."""
        return super().available and self._sensor_id in self.coordinator.data
