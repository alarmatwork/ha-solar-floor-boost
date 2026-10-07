"""Boost amount, adjustable from the UI."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SolarFloorBoostConfigEntry
from .boost import BoostManager
from .const import DEFAULT_DELTA
from .entity import BoostEntity


@dataclass(frozen=True, kw_only=True)
class BoostNumberDescription(NumberEntityDescription):
    """``key`` is also the BoostManager attribute the value is written to."""

    default: float


NUMBERS = (
    BoostNumberDescription(
        key="delta",
        icon="mdi:thermometer-plus",
        native_min_value=0.5,
        native_max_value=5,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.SLIDER,
        default=DEFAULT_DELTA,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolarFloorBoostConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(
        BoostNumber(entry.runtime_data, description) for description in NUMBERS
    )


class BoostNumber(BoostEntity, RestoreNumber):
    entity_description: BoostNumberDescription

    def __init__(
        self, manager: BoostManager, description: BoostNumberDescription
    ) -> None:
        super().__init__(manager, description.key)
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        value = (
            last.native_value
            if last and last.native_value is not None
            else self.entity_description.default
        )
        setattr(self._manager, self.entity_description.key, value)

    @property
    def native_value(self) -> float:
        return getattr(self._manager, self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        setattr(self._manager, self.entity_description.key, value)
        self.async_write_ha_state()
