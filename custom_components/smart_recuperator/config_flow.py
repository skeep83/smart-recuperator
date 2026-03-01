"""Smart Recuperator — Config Flow."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    DEFAULT_HUMIDITY_HIGH,
    DEFAULT_HUMIDITY_LOW,
    DEFAULT_NIGHT_SPEED,
    DEFAULT_HEATING_MIN_SPEED,
    DEFAULT_COLD_THRESHOLD,
    DEFAULT_HOT_THRESHOLD,
    DEFAULT_FILTER_WARN_DAYS,
    DEFAULT_NIGHT_START,
    DEFAULT_NIGHT_END,
    DEFAULT_NORMAL_SPEED,
)

_LOGGER = logging.getLogger(__name__)


class SmartRecuperatorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Smart Recuperator."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Step 1: Basic settings."""
        if user_input is not None:
            self._data = user_input
            return await self.async_step_devices()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional("heating_entity", default=""): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Optional("weather_entity", default="weather.forecast_home_assistant"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="weather")
                ),
            }),
            description_placeholders={
                "title": "Smart Recuperator",
            },
        )

    async def async_step_devices(self, user_input: dict[str, Any] | None = None):
        """Step 2: Add devices."""
        if user_input is not None:
            device = {
                "name": user_input["name"],
                "fan_entity": user_input["fan_entity"],
                "humidity_sensor": user_input.get("humidity_sensor", ""),
                "temperature_sensor": user_input.get("temperature_sensor", ""),
                "filter_timer_sensor": user_input.get("filter_timer_sensor", ""),
            }
            self._data.setdefault("devices", []).append(device)

            if user_input.get("add_another"):
                return await self.async_step_devices()

            return await self.async_step_modules()

        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Required("fan_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="fan")
                ),
                vol.Optional("humidity_sensor", default=""): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="humidity")
                ),
                vol.Optional("temperature_sensor", default=""): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="temperature")
                ),
                vol.Optional("filter_timer_sensor", default=""): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("add_another", default=False): bool,
            }),
        )

    async def async_step_modules(self, user_input: dict[str, Any] | None = None):
        """Step 3: Enable/disable modules and thresholds."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(
                title="Smart Recuperator",
                data=self._data,
            )

        return self.async_show_form(
            step_id="modules",
            data_schema=vol.Schema({
                vol.Optional("enable_humidity", default=True): bool,
                vol.Optional("enable_heating_sync", default=True): bool,
                vol.Optional("enable_dewpoint", default=True): bool,
                vol.Optional("enable_night_mode", default=True): bool,
                vol.Optional("enable_filter_alert", default=True): bool,
                vol.Optional("enable_weather", default=True): bool,
                vol.Optional("humidity_high", default=DEFAULT_HUMIDITY_HIGH): vol.All(
                    int, vol.Range(min=40, max=90)
                ),
                vol.Optional("humidity_low", default=DEFAULT_HUMIDITY_LOW): vol.All(
                    int, vol.Range(min=30, max=70)
                ),
                vol.Optional("night_speed", default=DEFAULT_NIGHT_SPEED): vol.All(
                    int, vol.Range(min=0, max=75)
                ),
                vol.Optional("normal_speed", default=DEFAULT_NORMAL_SPEED): vol.All(
                    int, vol.Range(min=25, max=100)
                ),
                vol.Optional("heating_min_speed", default=DEFAULT_HEATING_MIN_SPEED): vol.All(
                    int, vol.Range(min=0, max=50)
                ),
                vol.Optional("cold_threshold", default=DEFAULT_COLD_THRESHOLD): vol.All(
                    int, vol.Range(min=-10, max=10)
                ),
                vol.Optional("hot_threshold", default=DEFAULT_HOT_THRESHOLD): vol.All(
                    int, vol.Range(min=25, max=40)
                ),
                vol.Optional("filter_warn_days", default=DEFAULT_FILTER_WARN_DAYS): vol.All(
                    int, vol.Range(min=7, max=30)
                ),
                vol.Optional("night_start", default=DEFAULT_NIGHT_START): str,
                vol.Optional("night_end", default=DEFAULT_NIGHT_END): str,
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Options flow handler."""
        return SmartRecuperatorOptionsFlow(config_entry)


class SmartRecuperatorOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = self.config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("enable_humidity", default=data.get("enable_humidity", True)): bool,
                vol.Optional("enable_heating_sync", default=data.get("enable_heating_sync", True)): bool,
                vol.Optional("enable_dewpoint", default=data.get("enable_dewpoint", True)): bool,
                vol.Optional("enable_night_mode", default=data.get("enable_night_mode", True)): bool,
                vol.Optional("enable_filter_alert", default=data.get("enable_filter_alert", True)): bool,
                vol.Optional("enable_weather", default=data.get("enable_weather", True)): bool,
                vol.Optional("humidity_high", default=data.get("humidity_high", DEFAULT_HUMIDITY_HIGH)): vol.All(
                    int, vol.Range(min=40, max=90)
                ),
                vol.Optional("humidity_low", default=data.get("humidity_low", DEFAULT_HUMIDITY_LOW)): vol.All(
                    int, vol.Range(min=30, max=70)
                ),
                vol.Optional("night_speed", default=data.get("night_speed", DEFAULT_NIGHT_SPEED)): vol.All(
                    int, vol.Range(min=0, max=75)
                ),
                vol.Optional("normal_speed", default=data.get("normal_speed", DEFAULT_NORMAL_SPEED)): vol.All(
                    int, vol.Range(min=25, max=100)
                ),
                vol.Optional("night_start", default=data.get("night_start", DEFAULT_NIGHT_START)): str,
                vol.Optional("night_end", default=data.get("night_end", DEFAULT_NIGHT_END)): str,
            }),
        )
