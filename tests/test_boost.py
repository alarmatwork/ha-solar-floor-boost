from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry, async_fire_time_changed,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.setup import async_setup_component

DOMAIN = "solar_floor_boost"
A, B, OFF = "climate.bedroom", "climate.kitchen", "climate.garage"


async def _setup(hass: HomeAssistant):
    hass.states.async_set(A, "heat", {"temperature": 22.0, "target_temp_step": 0.5, "max_temp": 35})
    hass.states.async_set(B, "heat", {"temperature": 27.5, "max_temp": 35})
    hass.states.async_set(OFF, "off", {"temperature": 20.0})
    calls = []

    async def set_temp(call: ServiceCall):
        eid = call.data["entity_id"]
        eid = eid[0] if isinstance(eid, list) else eid
        calls.append((eid, call.data["temperature"]))
        st = hass.states.get(eid)
        hass.states.async_set(eid, st.state, {**st.attributes, "temperature": call.data["temperature"]})

    entry = MockConfigEntry(domain=DOMAIN, title="Solar Floor Boost", options={"climate_entities": [A, B, OFF], "max_temperature": 28})
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, "climate", {})
    hass.services.async_register("climate", "set_temperature", set_temp)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, calls


def t(hass, eid):
    return hass.states.get(eid).attributes["temperature"]


async def test_switch_boost_and_restore(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    entry, calls = await _setup(hass)
    assert hass.states.get("number.solar_floor_boost_boost_amount").state == "1.0"
    assert hass.states.get("number.solar_floor_boost_boost_duration").state == "120"
    await hass.services.async_call("switch", "turn_on", {"entity_id": "switch.solar_floor_boost_boost"}, blocking=True)
    assert t(hass, A) == 23.0
    assert t(hass, B) == 28.0  # capped by max_temperature
    assert t(hass, OFF) == 21.0  # boosted even when off
    assert hass.states.get("switch.solar_floor_boost_boost").state == "on"
    sensor = hass.states.get("sensor.solar_floor_boost_boost_ends")
    assert sensor.attributes["boosted"][A] == {"baseline": 22.0, "target": 23.0}

    freezer.tick(timedelta(minutes=121))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert t(hass, A) == 22.0 and t(hass, B) == 27.5 and t(hass, OFF) == 20.0
    assert hass.states.get("switch.solar_floor_boost_boost").state == "off"


async def test_service_override_reboost_manual_change(hass: HomeAssistant, freezer):
    entry, calls = await _setup(hass)
    await hass.services.async_call(DOMAIN, "start", {"delta": 2, "duration": 30, "climate_entities": [A]}, blocking=True)
    assert t(hass, A) == 24.0 and t(hass, B) == 27.5
    # Re-boost: applied to original baseline, not stacked; timer reset.
    freezer.tick(timedelta(minutes=20))
    await hass.services.async_call(DOMAIN, "start", {"delta": 3, "duration": 30, "climate_entities": [A, B]}, blocking=True)
    assert t(hass, A) == 25.0 and t(hass, B) == 28.0
    # Someone changes B manually -> must not be restored.
    hass.states.async_set(B, "heat", {"temperature": 21.0, "max_temp": 35})
    freezer.tick(timedelta(minutes=25))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert t(hass, A) == 25.0  # still boosted, timer was reset
    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert t(hass, A) == 22.0 and t(hass, B) == 21.0


async def test_unavailable_restored_later(hass: HomeAssistant):
    entry, calls = await _setup(hass)
    await hass.services.async_call(DOMAIN, "start", {}, blocking=True)
    hass.states.async_set(A, "unavailable", {})
    await hass.services.async_call(DOMAIN, "stop", {}, blocking=True)
    assert hass.states.get("sensor.solar_floor_boost_boost_ends").attributes["pending_restore"] == [A]
    assert t(hass, B) == 27.5
    hass.states.async_set(A, "heat", {"temperature": 23.0})
    await hass.async_block_till_done()
    assert t(hass, A) == 22.0
    assert hass.states.get("sensor.solar_floor_boost_boost_ends").attributes["pending_restore"] == []


async def test_survives_reload(hass: HomeAssistant, freezer):
    entry, calls = await _setup(hass)
    await hass.services.async_call(DOMAIN, "start", {"duration": 60}, blocking=True)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("switch.solar_floor_boost_boost").state == "on"
    freezer.tick(timedelta(minutes=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert t(hass, A) == 22.0


async def test_remove_entry_restores(hass: HomeAssistant):
    entry, calls = await _setup(hass)
    await hass.services.async_call(DOMAIN, "start", {}, blocking=True)
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert t(hass, A) == 22.0


async def test_config_flow(hass: HomeAssistant):
    hass.states.async_set(A, "heat", {"temperature": 22.0})
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"climate_entities": [A], "max_temperature": 26})
    assert result["type"] == "create_entry"
    assert result["options"] == {"climate_entities": [A], "max_temperature": 26}
    entry = result["result"]
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"climate_entities": [A], "max_temperature": 25})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert entry.options["max_temperature"] == 25


async def test_dashboard_card_registered(hass: HomeAssistant):
    from unittest.mock import AsyncMock, MagicMock, patch

    hass.config.components.add("frontend")
    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    with patch(f"custom_components.{DOMAIN}.add_extra_js_url") as add_js:
        assert await async_setup_component(hass, DOMAIN, {})
    (paths,), _ = hass.http.async_register_static_paths.call_args
    assert paths[0].url_path == "/solar_floor_boost/solar-floor-boost-card.js"
    assert paths[0].path.endswith("frontend/solar-floor-boost-card.js")
    add_js.assert_called_once_with(hass, "/solar_floor_boost/solar-floor-boost-card.js?v=1.1.0")
