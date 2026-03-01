"""Smart Recuperator — Intelligent climate automation for Blauberg/Siku recuperators."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PLATFORMS, CONF_DEVICES

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up via configuration.yaml (not used, config_flow only)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smart Recuperator from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR, Platform.BINARY_SENSOR])

    # Register automations
    await _setup_automations(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR, Platform.BINARY_SENSOR])

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def _setup_automations(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register climate automations for each device."""
    from homeassistant.helpers.event import (
        async_track_state_change_event,
        async_track_time_change,
    )
    from homeassistant.core import Event, callback
    import datetime

    data = entry.data
    devices = data.get(CONF_DEVICES, [])
    humidity_high = data.get("humidity_high", 65)
    humidity_low = data.get("humidity_low", 55)
    night_speed = data.get("night_speed", 25)
    heating_min_speed = data.get("heating_min_speed", 25)
    normal_speed = data.get("normal_speed", 50)
    cold_threshold = data.get("cold_threshold", 5)
    hot_threshold = data.get("hot_threshold", 30)
    night_start_str = data.get("night_start", "22:00")
    night_end_str = data.get("night_end", "07:00")
    weather_entity = data.get("weather_entity", "")
    heating_entity = data.get("heating_entity", "")

    night_start_parts = night_start_str.split(":")
    night_end_parts = night_end_str.split(":")
    night_start_h, night_start_m = int(night_start_parts[0]), int(night_start_parts[1])
    night_end_h, night_end_m = int(night_end_parts[0]), int(night_end_parts[1])

    unsub_callbacks = []

    # ── Humidity Control ──
    if data.get("enable_humidity", True):
        for dev in devices:
            humidity_sensor = dev.get("humidity_sensor", "")
            fan_entity = dev.get("fan_entity", "")
            dev_name = dev.get("name", "Recuperator")

            if not humidity_sensor or not fan_entity:
                continue

            @callback
            def _humidity_handler(event: Event, _fan=fan_entity, _sensor=humidity_sensor, _name=dev_name) -> None:
                new_state = event.data.get("new_state")
                if new_state is None:
                    return
                try:
                    hum = float(new_state.state)
                except (ValueError, TypeError):
                    return

                fan_state = hass.states.get(_fan)
                if not fan_state or fan_state.state != "on":
                    return

                if hum > humidity_high:
                    _LOGGER.info("Smart Recup: %s humidity %.0f%% > %d%%, boosting", _name, hum, humidity_high)
                    hass.async_create_task(
                        hass.services.async_call("fan", "set_percentage", {"entity_id": _fan, "percentage": 100})
                    )
                    hass.async_create_task(
                        hass.services.async_call("persistent_notification", "create", {
                            "title": f"💧 {_name}: Высокая влажность",
                            "message": f"Влажность {hum:.0f}% > {humidity_high}%. Boost активирован.",
                        })
                    )
                elif hum < humidity_low:
                    hass.async_create_task(
                        hass.services.async_call("fan", "set_percentage", {"entity_id": _fan, "percentage": normal_speed})
                    )

            unsub = async_track_state_change_event(hass, humidity_sensor, _humidity_handler)
            unsub_callbacks.append(unsub)

    # ── Heating Sync ──
    if data.get("enable_heating_sync", True) and heating_entity:
        fan_entities = [d["fan_entity"] for d in devices if d.get("fan_entity")]

        @callback
        def _heating_handler(event: Event) -> None:
            new_state = event.data.get("new_state")
            if new_state is None:
                return

            outdoor_temp = 10.0
            if weather_entity:
                weather = hass.states.get(weather_entity)
                if weather and weather.attributes.get("temperature") is not None:
                    outdoor_temp = float(weather.attributes["temperature"])

            if new_state.state == "on" and outdoor_temp < cold_threshold:
                _LOGGER.info("Smart Recup: Heating ON, outdoor %.1f°C < %d°C, reducing speed", outdoor_temp, cold_threshold)
                for fe in fan_entities:
                    hass.async_create_task(
                        hass.services.async_call("fan", "set_percentage", {"entity_id": fe, "percentage": heating_min_speed})
                    )
            elif new_state.state == "off":
                for fe in fan_entities:
                    hass.async_create_task(
                        hass.services.async_call("fan", "set_percentage", {"entity_id": fe, "percentage": normal_speed})
                    )

        unsub = async_track_state_change_event(hass, heating_entity, _heating_handler)
        unsub_callbacks.append(unsub)

    # ── Night Mode ──
    if data.get("enable_night_mode", True):
        fan_entities = [d["fan_entity"] for d in devices if d.get("fan_entity")]

        @callback
        def _night_start_handler(now: datetime.datetime) -> None:
            _LOGGER.info("Smart Recup: Night mode ON — speed %d%%", night_speed)
            for fe in fan_entities:
                hass.async_create_task(
                    hass.services.async_call("fan", "set_percentage", {"entity_id": fe, "percentage": night_speed})
                )

        @callback
        def _night_end_handler(now: datetime.datetime) -> None:
            _LOGGER.info("Smart Recup: Night mode OFF — speed %d%%", normal_speed)
            for fe in fan_entities:
                hass.async_create_task(
                    hass.services.async_call("fan", "set_percentage", {"entity_id": fe, "percentage": normal_speed})
                )

        unsub1 = async_track_time_change(hass, _night_start_handler, hour=night_start_h, minute=night_start_m, second=0)
        unsub2 = async_track_time_change(hass, _night_end_handler, hour=night_end_h, minute=night_end_m, second=0)
        unsub_callbacks.append(unsub1)
        unsub_callbacks.append(unsub2)

    # ── Weather Adaptation ──
    if data.get("enable_weather", True) and weather_entity:
        fan_entities = [d["fan_entity"] for d in devices if d.get("fan_entity")]
        bad_weather = {"rainy", "pouring", "lightning", "lightning-rainy", "hail"}
        good_weather = {"sunny", "clear-night", "partlycloudy", "cloudy"}

        @callback
        def _weather_handler(event: Event) -> None:
            new_state = event.data.get("new_state")
            if new_state is None:
                return

            condition = new_state.state
            outdoor_temp = float(new_state.attributes.get("temperature", 20))

            if condition in bad_weather or outdoor_temp > hot_threshold:
                _LOGGER.info("Smart Recup: Bad weather (%s, %.1f°C), reducing speed", condition, outdoor_temp)
                for fe in fan_entities:
                    hass.async_create_task(
                        hass.services.async_call("fan", "set_percentage", {"entity_id": fe, "percentage": 25})
                    )
            elif condition in good_weather and outdoor_temp <= hot_threshold:
                for fe in fan_entities:
                    hass.async_create_task(
                        hass.services.async_call("fan", "set_percentage", {"entity_id": fe, "percentage": normal_speed})
                    )

        unsub = async_track_state_change_event(hass, weather_entity, _weather_handler)
        unsub_callbacks.append(unsub)

    # Store unsub callbacks for cleanup
    hass.data[DOMAIN][entry.entry_id + "_unsub"] = unsub_callbacks
