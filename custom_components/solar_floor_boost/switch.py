"""Switch to start/stop the boost from the UI."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    async_add_entities([BoostSwitch(entry.runtime_data)])


class BoostSwitch(BoostEntity, SwitchEntity):
    _attr_icon = "mdi:heating-coil"

    def __init__(self, manager: BoostManager) -> None:
        super().__init__(manager, "boost")

    @property
    def is_on(self) -> bool:
        return self._manager.is_active

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._manager.async_start()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._manager.async_stop()
