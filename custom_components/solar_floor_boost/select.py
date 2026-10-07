"""Boost duration as presets (15m ... 12h) for the device page and dropdowns."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SolarFloorBoostConfigEntry
from .boost import BoostManager
from .entity import BoostEntity

# Minutes; keep in sync with DURATION_PRESETS in the dashboard card.
DURATION_PRESETS = (15, 30, 45, 60, 90, 120, 150, 180, 210, 240, 300, 360, 480, 720)


def format_duration(minutes: int) -> str:
    """15 -> '15m', 60 -> '1h', 90 -> '1h 30m'."""
    hours, rest = divmod(minutes, 60)
    if not hours:
        return f"{rest}m"
    return f"{hours}h {rest}m" if rest else f"{hours}h"


LABELS = {minutes: format_duration(minutes) for minutes in DURATION_PRESETS}
MINUTES = {label: minutes for minutes, label in LABELS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolarFloorBoostConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([BoostDurationSelect(entry.runtime_data)])


class BoostDurationSelect(BoostEntity, SelectEntity):
    """Another view of the duration number (which holds and restores the value)."""

    _attr_icon = "mdi:timer-outline"
    _attr_options = list(MINUTES)

    def __init__(self, manager: BoostManager) -> None:
        super().__init__(manager, "duration")

    @property
    def current_option(self) -> str:
        # The number (or an automation) may hold a non-preset value.
        nearest = min(
            DURATION_PRESETS, key=lambda preset: abs(preset - self._manager.duration)
        )
        return LABELS[nearest]

    async def async_select_option(self, option: str) -> None:
        self._manager.async_set_default("duration", MINUTES[option])
