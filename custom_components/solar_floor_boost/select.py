"""Boost duration as a list of presets (15m ... 12h)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import SolarFloorBoostConfigEntry
from .boost import BoostManager
from .const import DEFAULT_DURATION
from .entity import BoostEntity

# Minutes. Fine steps in the first hour, coarser after; the start action
# still accepts any number of minutes.
DURATION_PRESETS = (15, 30, 45, 60, 90, 120, 150, 180, 240, 300, 360, 480, 720)


def format_duration(minutes: int) -> str:
    """15 -> '15m', 60 -> '1h', 90 -> '1h 30m'."""
    hours, rest = divmod(minutes, 60)
    if not hours:
        return f"{rest}m"
    return f"{hours}h {rest}m" if rest else f"{hours}h"


LABELS = {minutes: format_duration(minutes) for minutes in DURATION_PRESETS}
MINUTES = {label: minutes for minutes, label in LABELS.items()}


def nearest_preset(minutes: float) -> int:
    return min(DURATION_PRESETS, key=lambda preset: abs(preset - minutes))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolarFloorBoostConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([BoostDurationSelect(entry.runtime_data)])


class BoostDurationSelect(BoostEntity, SelectEntity, RestoreEntity):
    _attr_icon = "mdi:timer-outline"
    _attr_options = list(MINUTES)

    def __init__(self, manager: BoostManager) -> None:
        super().__init__(manager, "duration")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        self._manager.duration = MINUTES.get(
            last.state if last else "", DEFAULT_DURATION
        )

    @property
    def current_option(self) -> str:
        return LABELS[nearest_preset(self._manager.duration)]

    async def async_select_option(self, option: str) -> None:
        self._manager.duration = MINUTES[option]
        self.async_write_ha_state()
