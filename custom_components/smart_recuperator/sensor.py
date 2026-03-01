"""Smart Recuperator — Sensor platform."""
from __future__ import annotations

import logging
import math

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN, CONF_DEVICES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up sensors from a config entry."""
    data = entry.data
    devices = data.get(CONF_DEVICES, [])
    weather_entity = data.get("weather_entity", "")

    sensors: list[SensorEntity] = []

    # Outdoor sensors (from weather)
    if weather_entity:
        sensors.append(OutdoorTempSensor(hass, entry, weather_entity))
        sensors.append(OutdoorHumiditySensor(hass, entry, weather_entity))

    for i, dev in enumerate(devices):
        dev_name = dev.get("name", f"Recuperator {i+1}")
        fan_entity = dev.get("fan_entity", "")
        humidity_sensor = dev.get("humidity_sensor", "")
        temp_sensor = dev.get("temperature_sensor", "")
        filter_sensor = dev.get("filter_timer_sensor", "")

        # Dew point sensor
        if humidity_sensor and temp_sensor:
            sensors.append(DewPointSensor(hass, entry, dev_name, temp_sensor, humidity_sensor, i))

        # Filter life sensor
        if filter_sensor:
            sensors.append(FilterLifeSensor(hass, entry, dev_name, filter_sensor, i))

        # Status sensor
        if fan_entity:
            sensors.append(StatusSensor(hass, entry, dev_name, dev, data, i))

    async_add_entities(sensors, True)


class OutdoorTempSensor(SensorEntity):
    """Outdoor temperature from weather entity."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer"

    def __init__(self, hass, entry, weather_entity):
        self._hass = hass
        self._entry = entry
        self._weather = weather_entity
        self._attr_unique_id = f"{entry.entry_id}_outdoor_temp"
        self._attr_name = "Рекуператор: Уличная температура"

    @property
    def native_value(self):
        state = self._hass.states.get(self._weather)
        if state and state.attributes.get("temperature") is not None:
            return round(float(state.attributes["temperature"]), 1)
        return None


class OutdoorHumiditySensor(SensorEntity):
    """Outdoor humidity from weather entity."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water-percent"

    def __init__(self, hass, entry, weather_entity):
        self._hass = hass
        self._entry = entry
        self._weather = weather_entity
        self._attr_unique_id = f"{entry.entry_id}_outdoor_humidity"
        self._attr_name = "Рекуператор: Уличная влажность"

    @property
    def native_value(self):
        state = self._hass.states.get(self._weather)
        if state and state.attributes.get("humidity") is not None:
            return round(float(state.attributes["humidity"]), 0)
        return None


class DewPointSensor(SensorEntity):
    """Dew point calculation using Magnus formula."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:water-thermometer"

    def __init__(self, hass, entry, dev_name, temp_sensor, hum_sensor, idx):
        self._hass = hass
        self._temp_sensor = temp_sensor
        self._hum_sensor = hum_sensor
        self._attr_unique_id = f"{entry.entry_id}_dewpoint_{idx}"
        self._attr_name = f"Точка росы: {dev_name}"

    @property
    def native_value(self):
        t_state = self._hass.states.get(self._temp_sensor)
        h_state = self._hass.states.get(self._hum_sensor)
        if not t_state or not h_state:
            return None
        try:
            t = float(t_state.state)
            rh = float(h_state.state)
        except (ValueError, TypeError):
            return None
        if rh <= 0:
            return 0
        alpha = (17.27 * t) / (237.7 + t) + math.log(rh / 100.0)
        dew = (237.7 * alpha) / (17.27 - alpha)
        return round(dew, 1)


class FilterLifeSensor(SensorEntity):
    """Filter life remaining in days."""

    _attr_native_unit_of_measurement = "д."
    _attr_icon = "mdi:air-filter"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, entry, dev_name, filter_sensor, idx):
        self._hass = hass
        self._filter_sensor = filter_sensor
        self._attr_unique_id = f"{entry.entry_id}_filter_{idx}"
        self._attr_name = f"Фильтр: {dev_name}"
        self._entry = entry

    @property
    def native_value(self):
        state = self._hass.states.get(self._filter_sensor)
        if not state or state.state in ("unavailable", "unknown"):
            return None
        return self._parse_filter_days(state.state)

    @staticmethod
    def _parse_filter_days(val: str) -> int | None:
        """Parse numeric or Russian-format filter timer."""
        import re
        val = val.strip()
        try:
            return int(float(val))
        except (ValueError, TypeError):
            pass
        d_match = re.search(r"(\d+)\s*д", val)
        h_match = re.search(r"(\d+)\s*ч", val)
        if d_match or h_match:
            days = int(d_match.group(1)) if d_match else 0
            hours = int(h_match.group(1)) if h_match else 0
            return days + round(hours / 24)
        return None

    @property
    def extra_state_attributes(self):
        """Add filter percentage and alarm status."""
        days = self.native_value
        warn_days = self._entry.data.get("filter_warn_days", 14)
        if days is None:
            return {"percentage": None, "needs_replacement": False}
        max_days = 90
        pct = min(100, max(0, round(days / max_days * 100)))
        return {
            "percentage": pct,
            "needs_replacement": days < warn_days,
        }


class StatusSensor(SensorEntity):
    """Smart status for each recuperator."""

    _attr_icon = "mdi:fan"

    def __init__(self, hass, entry, dev_name, dev_config, data, idx):
        self._hass = hass
        self._dev = dev_config
        self._data = data
        self._attr_unique_id = f"{entry.entry_id}_status_{idx}"
        self._attr_name = f"Рекуператор: {dev_name}"

    @property
    def native_value(self):
        fan = self._hass.states.get(self._dev.get("fan_entity", ""))
        if not fan or fan.state != "on":
            return "Выкл"

        # Check humidity
        hum_sensor = self._dev.get("humidity_sensor", "")
        if hum_sensor:
            hum_state = self._hass.states.get(hum_sensor)
            if hum_state:
                try:
                    hum = float(hum_state.state)
                    if hum > self._data.get("humidity_high", 65):
                        return "Осушение"
                except (ValueError, TypeError):
                    pass

        # Check night mode
        from datetime import datetime
        now = datetime.now()
        night_start = self._data.get("night_start", "22:00").split(":")
        night_end = self._data.get("night_end", "07:00").split(":")
        ns_h, ne_h = int(night_start[0]), int(night_end[0])
        if self._data.get("enable_night_mode", True):
            if now.hour >= ns_h or now.hour < ne_h:
                return "Ночной"

        # Check heating
        heating = self._data.get("heating_entity", "")
        if heating and self._data.get("enable_heating_sync", True):
            h_state = self._hass.states.get(heating)
            if h_state and h_state.state == "on":
                return "Эконом"

        return "Норма"
