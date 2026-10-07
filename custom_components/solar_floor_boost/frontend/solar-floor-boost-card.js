// Solar Floor Boost dashboard card: an entities card preconfigured with the
// integration's entities. Shows up under "By card" in the card picker.

const DOMAIN = "solar_floor_boost";

// translation_key -> [default entity_id, row name]
const ROWS = {
  boost: ["switch.solar_floor_boost_boost", "Boost"],
  delta: ["number.solar_floor_boost_boost_amount", "Boost amount"],
  duration: ["number.solar_floor_boost_boost_duration", "Boost duration"],
  boost_end: ["sensor.solar_floor_boost_boost_ends", "Boost ends"],
};

// Entity IDs can be renamed by the user, so look them up in the registry.
function findEntities(hass) {
  const ids = Object.fromEntries(
    Object.entries(ROWS).map(([key, [entityId]]) => [key, entityId])
  );
  for (const entry of Object.values(hass.entities || {})) {
    if (entry.platform === DOMAIN && entry.translation_key in ids) {
      ids[entry.translation_key] = entry.entity_id;
    }
  }
  return ids;
}

function entitiesCardConfig(config, ids) {
  return {
    type: "entities",
    title: config.title ?? "Floor heating boost",
    show_header_toggle: false,
    entities: [
      { entity: ids.boost, name: ROWS.boost[1] },
      { entity: ids.delta, name: ROWS.delta[1] },
      {
        type: "custom:solar-floor-boost-duration-row",
        entity: ids.duration,
        name: ROWS.duration[1],
      },
      {
        type: "conditional",
        conditions: [{ entity: ids.boost, state: "on" }],
        row: {
          entity: ids.boost_end,
          name: ROWS.boost_end[1],
          format: config.end_format ?? "relative",
        },
      },
    ],
  };
}

class SolarFloorBoostCard extends HTMLElement {
  static getStubConfig() {
    return { title: "Floor heating boost" };
  }

  setConfig(config) {
    this._config = config || {};
    this._card = undefined;
    this._build();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._card) {
      this._card.hass = hass;
    } else if (!this._building) {
      // hass updates arrive constantly; only start a build if none is
      // running, otherwise a busy home would restart it forever.
      this._build();
    }
  }

  async _build() {
    if (!this._config || !this._hass) return;
    const build = (this._buildId = (this._buildId || 0) + 1);
    this._building = true;
    try {
      const helpers = await window.loadCardHelpers();
      // A newer setConfig started another build meanwhile.
      if (build !== this._buildId) return;
      const card = helpers.createCardElement(
        entitiesCardConfig(this._config, findEntities(this._hass))
      );
      card.hass = this._hass;
      this.replaceChildren(card);
      this._card = card;
    } finally {
      if (build === this._buildId) this._building = false;
    }
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }
}

// Minutes. Fine steps in the first hour, coarser after.
const DURATION_PRESETS = [15, 30, 45, 60, 90, 120, 150, 180, 240, 300, 360, 480, 720];

// 15 -> "15m", 60 -> "1h", 90 -> "1h 30m"
function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const rest = Math.round(minutes % 60);
  if (!hours) return `${rest}m`;
  return rest ? `${hours}h ${rest}m` : `${hours}h`;
}

function nearestPreset(minutes) {
  let best = 0;
  DURATION_PRESETS.forEach((preset, i) => {
    if (Math.abs(preset - minutes) < Math.abs(DURATION_PRESETS[best] - minutes)) best = i;
  });
  return best;
}

// Slider row for the duration number entity: one evenly spaced step per
// preset and a "1h 30m" label. Usable in any entities card:
//   - type: custom:solar-floor-boost-duration-row
//     entity: number.solar_floor_boost_boost_duration
class SolarFloorBoostDurationRow extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error("entity is required");
    this._config = config;
    this._row = undefined;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._row) this._render();
    this._row.hass = hass;
    if (this._dragging) return;
    const state = hass.states[this._config.entity];
    const minutes = Number(state?.state);
    const known = Number.isFinite(minutes);
    this._input.value = known ? nearestPreset(minutes) : 0;
    this._input.disabled = !known;
    this._label.textContent = known ? formatDuration(minutes) : state?.state ?? "";
  }

  _render() {
    const style = document.createElement("style");
    style.textContent = `
      .wrap { display: flex; align-items: center; gap: 12px; }
      input { width: 140px; accent-color: var(--primary-color); cursor: pointer; }
      .label { min-width: 4.5em; text-align: end; white-space: nowrap; }
    `;
    // HA's own row element gives the icon/name layout of the other rows.
    const row = document.createElement("hui-generic-entity-row");
    row.config = this._config;
    const wrap = document.createElement("div");
    wrap.className = "wrap";
    this._input = Object.assign(document.createElement("input"), {
      type: "range",
      min: 0,
      max: DURATION_PRESETS.length - 1,
      step: 1,
    });
    this._label = Object.assign(document.createElement("span"), {
      className: "label",
    });
    this._input.addEventListener("click", (ev) => ev.stopPropagation());
    this._input.addEventListener("input", () => {
      this._dragging = true;
      this._label.textContent = formatDuration(DURATION_PRESETS[this._input.value]);
    });
    this._input.addEventListener("change", () => {
      this._dragging = false;
      this._hass.callService("number", "set_value", {
        entity_id: this._config.entity,
        value: DURATION_PRESETS[this._input.value],
      });
    });
    wrap.append(this._input, this._label);
    row.append(wrap);
    this.replaceChildren(style, row);
    this._row = row;
  }
}

// The frontend's app bundle installs a scoped custom element registry
// polyfill that replaces window.customElements. This module is loaded in
// parallel and can run first; elements defined on the old registry are then
// invisible to Lovelace (endless spinner in the card picker). So wait until
// the app has defined <home-assistant> on the current registry.
async function whenAppReady(timeoutMs = 60000) {
  const start = Date.now();
  while (
    !window.customElements.get("home-assistant") &&
    Date.now() - start < timeoutMs
  ) {
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
}

function register() {
  const registry = window.customElements;
  if (!registry.get("solar-floor-boost-duration-row")) {
    registry.define("solar-floor-boost-duration-row", SolarFloorBoostDurationRow);
  }
  if (registry.get("solar-floor-boost-card")) return;
  registry.define("solar-floor-boost-card", SolarFloorBoostCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "solar-floor-boost-card",
    name: "Solar Floor Boost",
    description: "Start/stop the boost, set amount and duration, see when it ends.",
    preview: true,
    // HA 2026.6+: offer this card in "By entity" for any of our entities.
    getEntitySuggestion: (hass, entityId) =>
      hass.entities?.[entityId]?.platform === DOMAIN
        ? [
            {
              label: "Solar Floor Boost",
              config: { type: "custom:solar-floor-boost-card" },
            },
          ]
        : null,
    documentationURL: "https://github.com/alarmatwork/ha-solar-floor-boost",
  });
}

whenAppReady().then(register);
