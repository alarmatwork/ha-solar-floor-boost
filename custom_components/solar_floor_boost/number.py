"""Boost amount and duration, adjustable from the UI."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import SolarFloorBoostConfigEntry
from .boost import BoostManager
from .const import DEFAULT_DELTA, DEFAULT_DURATION
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
    BoostNumberDescription(
        key="duration",
        icon="mdi:timer-outline",
        device_class=NumberDeviceClass.DURATION,
        native_min_value=15,
        native_max_value=720,
        native_step=15,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        mode=NumberMode.SLIDER,
        default=DEFAULT_DURATION,
        # The preset select is the UI control; this stays for cards and
        # automations that use the minutes value.
        entity_registry_visible_default=False,
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
        self._manager.async_set_default(self.entity_description.key, value)

    @property
    def native_value(self) -> float:
        return getattr(self._manager, self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        self._manager.async_set_default(self.entity_description.key, value)
