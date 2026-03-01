"""Smart Recuperator — Binary Sensor platform."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_DEVICES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up binary sensors from a config entry."""
    data = entry.data
    devices = data.get(CONF_DEVICES, [])

    sensors: list[BinarySensorEntity] = []

    for i, dev in enumerate(devices):
        dev_name = dev.get("name", f"Recuperator {i+1}")
        filter_sensor = dev.get("filter_timer_sensor", "")

        if filter_sensor:
            sensors.append(FilterAlertBinarySensor(hass, entry, dev_name, filter_sensor, data, i))

    if sensors:
        async_add_entities(sensors, True)


class FilterAlertBinarySensor(BinarySensorEntity):
    """Binary sensor that is ON when filter needs replacement."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:air-filter"

    def __init__(self, hass, entry, dev_name, filter_sensor, data, idx):
        self._hass = hass
        self._filter_sensor = filter_sensor
        self._data = data
        self._attr_unique_id = f"{entry.entry_id}_filter_alert_{idx}"
        self._attr_name = f"Фильтр замена: {dev_name}"

    @property
    def is_on(self) -> bool | None:
        """Return True if filter needs replacement."""
        state = self._hass.states.get(self._filter_sensor)
        if not state or state.state in ("unavailable", "unknown"):
            return None

        days = self._parse_days(state.state)
        if days is None:
            return None

        warn_days = self._data.get("filter_warn_days", 14)
        return days < warn_days

    @staticmethod
    def _parse_days(val: str) -> int | None:
        """Parse filter timer value to days."""
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
