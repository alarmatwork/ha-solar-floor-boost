"""Sensor showing when the current boost ends."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SolarFloorBoostConfigEntry
from .boost import BoostManager
from .entity import BoostEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolarFloorBoostConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([BoostEndSensor(entry.runtime_data)])


class BoostEndSensor(BoostEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:timer-sand"

    def __init__(self, manager: BoostManager) -> None:
        super().__init__(manager, "boost_end")

    @property
    def native_value(self) -> datetime | None:
        return self._manager.ends_at

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "delta": self._manager.active_delta,
            "boosted": {
                entity_id: {"baseline": rec.baseline, "target": rec.target}
                for entity_id, rec in self._manager.boosted.items()
            },
            "pending_restore": self._manager.pending_restore,
        }
