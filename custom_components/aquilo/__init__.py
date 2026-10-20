"""The Aquilo integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import CONF_EXCLUDED_SENSORS, DOMAIN
from .coordinator import AquiloDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

type AquiloConfigEntry = ConfigEntry[AquiloDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: AquiloConfigEntry) -> bool:
    """Set up Aquilo from a config entry."""
    coordinator = AquiloDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    _async_remove_excluded_devices(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


def _async_remove_excluded_devices(hass: HomeAssistant, entry: AquiloConfigEntry) -> None:
    """Remove devices (and their entities) of sensors the user excluded.

    Excluding a sensor only stops its entities from being created; a device
    that existed before the exclusion would otherwise stay as a permanently
    unavailable leftover.
    """
    excluded = {
        (DOMAIN, sensor_id)
        for sensor_id in entry.options.get(CONF_EXCLUDED_SENSORS, [])
    }
    if not excluded:
        return
    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        if device.identifiers & excluded:
            device_registry.async_remove_device(device.id)


async def async_unload_entry(hass: HomeAssistant, entry: AquiloConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: AquiloConfigEntry) -> None:
    """Reload the entry when its options (e.g. scan interval) change."""
    await hass.config_entries.async_reload(entry.entry_id)
