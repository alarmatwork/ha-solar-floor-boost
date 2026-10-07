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

    default: float  # in BoostManager units
    # BoostManager value = entity value * scale (duration: hours -> minutes).
    scale: float = 1
    # Restored values in this unit are already BoostManager units (the
    # duration was in minutes up to 1.5.x).
    legacy_unit: str | None = None


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
        # Hours, so Home Assistant displays it as "4h 45m"; 15-minute steps.
        native_min_value=0.25,
        native_max_value=12,
        native_step=0.25,
        native_unit_of_measurement=UnitOfTime.HOURS,
        mode=NumberMode.SLIDER,
        default=DEFAULT_DURATION,
        scale=60,
        legacy_unit=UnitOfTime.MINUTES,
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
        description = self.entity_description
        last = await self.async_get_last_number_data()
        if last is None or last.native_value is None:
            value = description.default
        elif last.native_unit_of_measurement == description.legacy_unit:
            value = last.native_value
        else:
            value = last.native_value * description.scale
        self._manager.async_set_default(description.key, value)

    @property
    def native_value(self) -> float:
        description = self.entity_description
        return getattr(self._manager, description.key) / description.scale

    async def async_set_native_value(self, value: float) -> None:
        description = self.entity_description
        self._manager.async_set_default(description.key, value * description.scale)
