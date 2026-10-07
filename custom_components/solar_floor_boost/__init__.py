"""Solar Floor Boost: temporarily raise thermostat targets to store surplus solar as heat."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .boost import BoostManager
from .const import (
    ATTR_CLIMATE_ENTITIES,
    ATTR_DELTA,
    ATTR_DURATION,
    DOMAIN,
    SERVICE_START,
    SERVICE_STOP,
)

PLATFORMS = [Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

CARD_URL = f"/{DOMAIN}/solar-floor-boost-card.js"
CARD_PATH = Path(__file__).parent / "frontend" / "solar-floor-boost-card.js"

START_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DELTA): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=10)
        ),
        vol.Optional(ATTR_DURATION): vol.All(
            vol.Coerce(float), vol.Range(min=1, max=1440)
        ),
        vol.Optional(ATTR_CLIMATE_ENTITIES): cv.entities_domain(CLIMATE_DOMAIN),
    }
)

type SolarFloorBoostConfigEntry = ConfigEntry[BoostManager]


def _get_manager(hass: HomeAssistant) -> BoostManager:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    raise ServiceValidationError(
        translation_domain=DOMAIN, translation_key="not_loaded"
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def start(call: ServiceCall) -> None:
        await _get_manager(hass).async_start(
            delta=call.data.get(ATTR_DELTA),
            duration=call.data.get(ATTR_DURATION),
            entity_ids=call.data.get(ATTR_CLIMATE_ENTITIES),
        )

    async def stop(call: ServiceCall) -> None:
        await _get_manager(hass).async_stop()

    hass.services.async_register(DOMAIN, SERVICE_START, start, schema=START_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_STOP, stop)
    await _async_register_card(hass)
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the dashboard card and load it in every frontend session."""
    if hass.http is None or "frontend" not in hass.config.components:
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=True)]
    )
    # Version in the URL so browsers fetch the new file after an update.
    version = (await async_get_integration(hass, DOMAIN)).version
    add_extra_js_url(hass, f"{CARD_URL}?v={version}")


async def async_setup_entry(
    hass: HomeAssistant, entry: SolarFloorBoostConfigEntry
) -> bool:
    # 1.3.0 briefly had the duration as a select entity; it's the number
    # entity again (as before), with presets in the dashboard card.
    registry = er.async_get(hass)
    if old := registry.async_get_entity_id(
        Platform.SELECT, DOMAIN, f"{entry.entry_id}_duration"
    ):
        registry.async_remove(old)

    manager = BoostManager(hass, entry)
    await manager.async_load()
    entry.runtime_data = manager
    entry.async_on_unload(manager.async_shutdown)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SolarFloorBoostConfigEntry
) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(
    hass: HomeAssistant, entry: SolarFloorBoostConfigEntry
) -> None:
    """Put thermostats back before the integration disappears."""
    manager = BoostManager(hass, entry)
    await manager.async_load(resume=False)
    await manager.async_stop()
    manager.async_shutdown()
    await manager.async_remove_storage()


async def _async_update_listener(
    hass: HomeAssistant, entry: SolarFloorBoostConfigEntry
) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
