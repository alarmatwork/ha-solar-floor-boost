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
      { entity: ids.duration, name: ROWS.duration[1] },
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
    this._build();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._card) {
      this._card.hass = hass;
    } else {
      this._build();
    }
  }

  async _build() {
    if (!this._config || !this._hass) return;
    const build = (this._buildId = (this._buildId || 0) + 1);
    const helpers = await window.loadCardHelpers();
    // A newer setConfig/hass call started another build meanwhile.
    if (build !== this._buildId) return;
    const card = helpers.createCardElement(
      entitiesCardConfig(this._config, findEntities(this._hass))
    );
    card.hass = this._hass;
    this.replaceChildren(card);
    this._card = card;
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }
}

if (!customElements.get("solar-floor-boost-card")) {
  customElements.define("solar-floor-boost-card", SolarFloorBoostCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "solar-floor-boost-card",
    name: "Solar Floor Boost",
    description: "Start/stop the boost, set amount and duration, see when it ends.",
    preview: true,
    documentationURL: "https://github.com/alarmatwork/ha-solar-floor-boost",
  });
}
