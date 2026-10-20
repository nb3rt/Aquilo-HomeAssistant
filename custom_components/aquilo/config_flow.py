"""Config flow for the Aquilo integration."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_EXCLUDED_SENSORS,
    CONF_OVERFLOW_PCT,
    CONF_STALE_HOURS,
    DEFAULT_OVERFLOW_PCT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STALE_HOURS,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    REQUEST_TIMEOUT,
)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


async def _async_validate_host(hass: HomeAssistant, host: str) -> dict[str, Any]:
    """Try to read /state from the given host. Raises on failure."""
    session = async_get_clientsession(hass)
    async with asyncio.timeout(REQUEST_TIMEOUT):
        response = await session.get(f"http://{host}/state")
        response.raise_for_status()
        return await response.json(content_type=None)


class AquiloConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Aquilo."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            try:
                payload = await _async_validate_host(self.hass, host)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                if not payload.get("sensors"):
                    errors["base"] = "no_sensors"
                else:
                    title = payload.get("from") or host
                    return self.async_create_entry(
                        title=f"Aquilo ({title})",
                        data={CONF_HOST: host},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return AquiloOptionsFlow()


class AquiloOptionsFlow(OptionsFlow):
    """Handle Aquilo options: polling, alert thresholds, excluded sensors."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._options: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage polling interval and alert thresholds."""
        if user_input is not None:
            self._options.update(user_input)
            return await self.async_step_sensors()

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
                vol.Required(
                    CONF_STALE_HOURS,
                    default=options.get(CONF_STALE_HOURS, DEFAULT_STALE_HOURS),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=24 * 30)),
                vol.Required(
                    CONF_OVERFLOW_PCT,
                    default=options.get(CONF_OVERFLOW_PCT, DEFAULT_OVERFLOW_PCT),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose sensors to leave out of Home Assistant."""
        excluded: list[str] = list(
            self.config_entry.options.get(CONF_EXCLUDED_SENSORS, [])
        )

        if user_input is not None:
            self._options[CONF_EXCLUDED_SENSORS] = user_input.get(
                CONF_EXCLUDED_SENSORS, []
            )
            return self.async_create_entry(data=self._options)

        choices: dict[str, str] = {}
        coordinator = getattr(self.config_entry, "runtime_data", None)
        if coordinator is not None and coordinator.data:
            for sensor_id, data in coordinator.data.items():
                choices[sensor_id] = data.get("name") or f"Aquilo {sensor_id}"
        # Keep already excluded ids selectable even when the device no longer
        # reports them, otherwise they could never be included again.
        for sensor_id in excluded:
            choices.setdefault(sensor_id, sensor_id)

        schema = vol.Schema(
            {
                vol.Optional(CONF_EXCLUDED_SENSORS, default=excluded): cv.multi_select(
                    choices
                )
            }
        )
        return self.async_show_form(step_id="sensors", data_schema=schema)
