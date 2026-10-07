"""Config flow for Solar Floor Boost."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CLIMATES,
    CONF_MAX_TEMPERATURE,
    DEFAULT_MAX_TEMPERATURE,
    DOMAIN,
)

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIMATES): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=CLIMATE_DOMAIN, multiple=True)
        ),
        vol.Required(CONF_MAX_TEMPERATURE): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=10,
                max=35,
                step=0.5,
                unit_of_measurement=UnitOfTemperature.CELSIUS,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
    }
)


class SolarFloorBoostConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 3

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="Solar Floor Boost", data={}, options=user_input
            )
        suggested = {
            CONF_CLIMATES: self.hass.states.async_entity_ids(CLIMATE_DOMAIN),
            CONF_MAX_TEMPERATURE: DEFAULT_MAX_TEMPERATURE,
        }
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, suggested),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SolarFloorBoostOptionsFlow()


class SolarFloorBoostOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                SCHEMA, self.config_entry.options
            ),
        )
