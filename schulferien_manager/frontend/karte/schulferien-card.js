/* Schulferien-Card – Lovelace Custom Card für den Schulferien & Feiertage Manager
 *
 * Minimale Konfiguration:
 *   type: custom:schulferien-card
 *   prefix: schulferien_bayern
 *
 * Alle Optionen sind über den visuellen Editor einstellbar.
 */
const CARD_VERSION = "1.4.1";
console.info(`%c SCHULFERIEN-CARD %c v${CARD_VERSION} `,
  "color:#1a1408;background:#e8a23d;font-weight:700", "color:#e8a23d;background:#1f2630");

const ENTITY_KEYS = [
  "naechste_schulferien", "naechster_feiertag",
  "heute_schulfrei", "morgen_schulfrei",
  "heute_feiertag", "morgen_feiertag", "status", "kalender",
];

/* Alle vom Add-on angelegten Regionen aus den Entitäten ableiten. */
function detectRegions(hass) {
  const found = new Map();
  for (const eid of Object.keys(hass.states)) {
    const m = eid.match(/^(?:sensor|binary_sensor)\.((?:schulferien|feiertage)_.+)$/);
    if (!m) continue;
    const oid = m[1];
    for (const key of ENTITY_KEYS) {
      const idx = oid.indexOf(`_${key}`);
      if (idx > 0) {
        const prefix = oid.slice(0, idx);
        const rest = oid.slice(idx + key.length + 1);
        const suffix = rest.startsWith("_") ? rest.slice(1) : "";
        found.set(`${prefix}|${suffix}`, { prefix, suffix });
        break;
      }
    }
  }
  return [...found.values()].sort((a, b) => a.prefix.localeCompare(b.prefix));
}

const DEFAULTS = {
  show_banner: true,
  demo_banner: false,
  show_badges: true,
  badge_heute_schulfrei: true,
  badge_morgen_schulfrei: true,
  badge_heute_feiertag: true,
  badge_morgen_feiertag: true,
  show_strip: true,
  strip_days: 14,
  show_feiertag: true,
  show_ferien: true,
  termine_anzahl: 4,
  suffix: "",
};

class SchulferienCard extends HTMLElement {
  setConfig(config) {
    if (!config.prefix) {
      throw new Error('Bitte "prefix" angeben oder im visuellen Editor eine Region wählen.');
    }
    this._config = { ...DEFAULTS, ...config };
    this._fp = null;
  }

  set hass(hass) {
    this._hass = hass;
    const fp = JSON.stringify(this._relevant());
    if (fp !== this._fp) {
      this._fp = fp;
      this._render();
    }
  }

  _id(key) {
    const sfx = this._config.suffix ? `_${this._config.suffix}` : "";
    return `${this._config.prefix}_${key}${sfx}`;
  }

  _st(domain, key) {
    return this._hass.states[`${domain}.${this._id(key)}`] || null;
  }

  _relevant() {
    const ids = [
      ["binary_sensor", "heute_schulfrei"], ["binary_sensor", "morgen_schulfrei"],
      ["binary_sensor", "heute_feiertag"], ["binary_sensor", "morgen_feiertag"],
      ["sensor", "naechster_feiertag"], ["sensor", "naechste_schulferien"],
      ["sensor", "status"],
    ];
    const kal = this._st("sensor", "kalender");
    return [this._config, ...ids.map(([d, k]) => {
      const s = this._st(d, k);
      return s ? [s.state, s.attributes] : null;
    }), kal ? [kal.state, kal.attributes.zeitraum_von, kal.attributes.zeitraum_bis] : null];
  }

  _fmt(iso) {
    if (!iso) return "–";
    return new Date(iso + "T00:00:00").toLocaleDateString("de-DE",
      { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  _heute() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  /* Tage von heute bis zum ISO-Datum (negativ = Vergangenheit). */
  _tage(iso) {
    if (!iso) return null;
    const heute = new Date(this._heute() + "T00:00:00");
    return Math.round((new Date(iso + "T00:00:00") - heute) / 86400000);
  }

  _in(n) {
    if (n === null || n === undefined) return "";
    return n === 0 ? "heute" : n === 1 ? "morgen" : `in ${n} Tagen`;
  }

  _badge(label, st, holidayStyle) {
    if (!st) return "";
    const on = st.state === "on";
    const why = st.attributes.grund || st.attributes.name || "";
    return `<div class="badge ${on ? (holidayStyle ? "on ft" : "on") : ""}" title="${why}">
      ${label}: <b>${on ? "Ja" : "Nein"}</b></div>`;
  }

  _render() {
    if (!this._hass || !this._config) return;
    const c = this._config;

    const hs = this._st("binary_sensor", "heute_schulfrei");
    const ms = this._st("binary_sensor", "morgen_schulfrei");
    const hf = this._st("binary_sensor", "heute_feiertag");
    const mf = this._st("binary_sensor", "morgen_feiertag");
    const nf = this._st("sensor", "naechster_feiertag");
    const ns = this._st("sensor", "naechste_schulferien");
    const combined = this._st("sensor", "status");
    const kal = this._st("sensor", "kalender");

    if (!hs && !hf && !combined) {
      this.innerHTML = `<ha-card><div class="sfc-wrap">
        Keine Entitäten mit Präfix <code>${c.prefix}</code> gefunden.<br>
        Region im visuellen Editor wählen oder Präfix aus der Infobox „Entitäten"
        im Add-on übernehmen (z. B. <code>schulferien_bayern</code>).</div></ha-card>`;
      return;
    }

    const a = combined ? combined.attributes : {};
    const days = Math.max(3, Math.min(14, Number(c.strip_days) || 14));
    const strip = ((nf?.attributes.vorschau) || a.vorschau || []).slice(0, days);
    const nextFt = nf
      ? { name: nf.state !== "unknown" ? nf.state : null, datum: nf.attributes.datum, in: nf.attributes.in_tagen }
      : { name: a.naechster_feiertag, datum: a.naechster_feiertag_datum, in: a.naechster_feiertag_in_tagen };
    const nextFe = ns
      ? { name: ns.state !== "unknown" ? ns.state : null, beginn: ns.attributes.beginn,
          ende: ns.attributes.ende, in: ns.attributes.in_tagen, aktuell: ns.attributes.aktuell_ferien,
          aktuellEnde: ns.attributes.aktuell_ferien_ende }
      : { name: a.naechste_schulferien, beginn: a.schulferien_beginn,
          ende: a.schulferien_ende, in: a.schulferien_in_tagen, aktuell: a.aktuell_ferien,
          aktuellEnde: a.aktuell_ferien_ende };

    const bannerData = nextFe.aktuell
      ? { name: nextFe.aktuell, ende: nextFe.aktuellEnde, demo: false }
      : (c.demo_banner === true
          ? { name: nextFe.name || "Sommerferien", ende: nextFe.ende || null, demo: true }
          : null);
    const banner = (c.show_banner !== false && bannerData)
      ? `<div class="banner">🏖️ <span>Es sind <b>${bannerData.name}</b>${
          bannerData.ende ? ` bis ${this._fmt(bannerData.ende)}` : "!"}</span>${
          bannerData.demo ? '<span class="demo-chip">Demo</span>' : ""}</div>`
      : "";

    const bf = {
      hs: c.show_badges !== false && c.badge_heute_schulfrei !== false,
      ms: c.show_badges !== false && c.badge_morgen_schulfrei !== false,
      hf: c.show_badges !== false && c.badge_heute_feiertag !== false,
      mf: c.show_badges !== false && c.badge_morgen_feiertag !== false,
    };
    const badgeItems = combined
      ? ((bf.hs || bf.ms || bf.hf || bf.mf)
          ? [`<div class="badge ${["Ferien", "Feiertag", "Wochenende"].includes(combined.state) ? "on" : ""}">
               Heute: <b>${combined.state}</b></div>`]
          : [])
      : [
          bf.hs ? this._badge("Heute schulfrei", hs, false) : "",
          bf.ms ? this._badge("Morgen schulfrei", ms, false) : "",
          bf.hf ? this._badge("Heute Feiertag", hf, true) : "",
          bf.mf ? this._badge("Morgen Feiertag", mf, true) : "",
        ];
    const badgesJoined = badgeItems.join("");
    const badges = badgesJoined ? `<div class="badges">${badgesJoined}</div>` : "";

    const stripHtml = c.show_strip && strip.length ? `
      <div class="strip">${strip.map((d, i) => `
        <div class="d ${d.status} ${i === 0 ? "today" : ""}"
             title="${d.weekday} ${this._fmt(d.date)} – ${d.status}">
          <div class="box"></div><span>${d.weekday}<br>${d.day}.</span>
        </div>`).join("")}
      </div>
      <div class="legend">
        <span><i class="lg-ferien"></i>Ferien</span>
        <span><i class="lg-feiertag"></i>Feiertag</span>
        <span><i class="lg-we"></i>Wochenende</span>
      </div>` : "";

    // Termine sammeln und chronologisch sortieren
    const events = [];
    const row = (cls, ico, name, dates, when) => `<div class="row ${cls}">
      <span class="ico">${ico}</span>
      <div class="rowbody">
        <span class="nm">${name}${dates ? ` <small>${dates}</small>` : ""}</span>
        <span class="when">${when}</span>
      </div></div>`;
    const anzahl = Math.max(1, Math.min(12, Number(c.termine_anzahl) || 4));
    const kalFt = kal?.attributes.feiertage;
    const kalFe = kal?.attributes.schulferien;

    if (kalFt || kalFe) {
      // Add-on ab v1.4.0: alle Termine der nächsten ~18 Monate stehen im Kalender-Sensor
      const heute = this._heute();
      if (c.show_feiertag) {
        for (const f of kalFt || []) {
          if (!f.datum || f.datum < heute) continue;
          events.push({ d: f.datum,
            html: row("", "★", f.name, this._fmt(f.datum), this._in(this._tage(f.datum))) });
        }
      }
      if (c.show_ferien) {
        for (const f of kalFe || []) {
          if (!f.ende || f.ende < heute) continue;
          if (f.beginn <= heute) {
            if (banner) continue;  // laufende Ferien zeigt schon der Banner
            events.push({ d: "0000-00-00",
              html: row("live", "🏖️", f.name, `bis ${this._fmt(f.ende)}`, "läuft gerade") });
          } else {
            const zeitraum = f.beginn === f.ende
              ? this._fmt(f.beginn)
              : `${this._fmt(f.beginn)} – ${this._fmt(f.ende)}`;
            events.push({ d: f.beginn,
              html: row("", "🏖️", f.name, zeitraum, this._in(this._tage(f.beginn))) });
          }
        }
      }
    } else {
      // Add-on vor v1.4.0: nur der jeweils nächste Termin je Art
      if (c.show_ferien && nextFe.aktuell && !banner) {
        events.push({ d: "0000-00-00", html: row("live", "🏖️", nextFe.aktuell, "", "läuft gerade") });
      }
      if (c.show_feiertag && nextFt.name) {
        events.push({ d: nextFt.datum || "9999-12-31",
          html: row("", "★", nextFt.name, this._fmt(nextFt.datum), this._in(nextFt.in)) });
      }
      if (c.show_ferien && nextFe.name) {
        events.push({ d: nextFe.beginn || "9999-12-31",
          html: row("", "🏖️", nextFe.name,
            `${this._fmt(nextFe.beginn)} – ${this._fmt(nextFe.ende)}`, this._in(nextFe.in)) });
      }
    }
    events.sort((x, y) => x.d.localeCompare(y.d));
    const rows = events.slice(0, anzahl).map((e) => e.html);
    const rowsHtml = (c.show_feiertag || c.show_ferien)
      ? `<div class="rows">${rows.join("") || "<small>Keine anstehenden Termine.</small>"}</div>`
      : "";

    this.innerHTML = `
      <ha-card ${c.title ? `header="${c.title}"` : ""}>
        <div class="sfc-wrap">
          ${banner}
          ${badges}
          ${stripHtml}
          ${rowsHtml}
        </div>
      </ha-card>
      <style>
        .sfc-wrap{padding:0 16px 16px;display:flex;flex-direction:column;gap:12px}
        ha-card:not([header]) .sfc-wrap{padding-top:16px}
        .banner{display:flex;align-items:center;gap:9px;
          background:linear-gradient(100deg,#e8a23d,#f2c178);color:#1a1408;
          border-radius:10px;padding:10px 14px;font-size:.95rem;
          box-shadow:0 2px 8px rgba(232,162,61,.25)}
        .banner b{font-weight:700}
        .banner .demo-chip{margin-left:auto;font-size:.68rem;font-weight:600;
          background:rgba(26,20,8,.18);padding:2px 8px;border-radius:99px;letter-spacing:.04em}
        .badges{display:flex;flex-wrap:wrap;gap:6px}
        .badge{display:inline-flex;align-items:center;gap:4px;height:30px;box-sizing:border-box;
          font-size:.8rem;line-height:1;border-radius:8px;padding:0 11px;
          background:var(--secondary-background-color);color:var(--secondary-text-color);
          border:1px solid var(--divider-color)}
        .badge b{font-size:inherit;line-height:1}
        .badge.on{color:var(--success-color,#4cc38a)}
        .badge.on.ft{color:#7aa2ff}
        .strip{display:flex;gap:3px}
        .strip .d{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;
          font-size:.62rem;line-height:1.15;text-align:center;color:var(--secondary-text-color);min-width:0}
        .strip .box{width:100%;height:20px;border-radius:5px;
          background:var(--secondary-background-color);border:1px solid var(--divider-color)}
        .strip .d.today .box{border:2px solid var(--primary-color,#03a9f4);
          box-shadow:0 0 6px rgba(3,169,244,.45)}
        .strip .d.today span{color:var(--primary-text-color);font-weight:700}
        .strip .d.ferien .box{background:rgba(232,162,61,.55);border-color:#e8a23d}
        .strip .d.feiertag .box{background:rgba(122,162,255,.6);border-color:#7aa2ff}
        .strip .d.wochenende .box{background:rgba(138,148,163,.25)}
        .legend{display:flex;gap:12px;font-size:.68rem;color:var(--secondary-text-color);margin-top:-6px}
        .legend i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:4px}
        .lg-ferien{background:#e8a23d}.lg-feiertag{background:#7aa2ff}.lg-we{background:rgba(138,148,163,.45)}
        .rows{display:flex;flex-direction:column;gap:10px}
        .row{display:flex;gap:10px;align-items:flex-start;font-size:.9rem}
        .row .ico{width:18px;text-align:center;flex:none;line-height:1.4}
        .rowbody{display:flex;flex-direction:column;gap:1px;min-width:0}
        .row .nm{overflow:hidden;text-overflow:ellipsis}
        .row .nm small{color:var(--secondary-text-color);white-space:nowrap}
        .row .when{color:var(--secondary-text-color);font-size:.78rem}
        .row.live .nm{color:var(--success-color,#4cc38a)}
      </style>`;
  }

  getCardSize() { return 4; }

  static getConfigElement() {
    return document.createElement("schulferien-card-editor");
  }

  static getStubConfig(hass) {
    const first = hass ? detectRegions(hass)[0] : null;
    const stub = { prefix: first ? first.prefix : "schulferien_bayern" };
    if (first && first.suffix) stub.suffix = first.suffix;
    return stub;
  }
}

/* ------------------------------- Visueller Editor ------------------------------- */

const EDITOR_LABELS = {
  region: "Region (vom Add-on angelegt)",
  title: "Titel",
  show_banner: "Ferien-Banner anzeigen (wenn Ferien laufen)",
  demo_banner: "Demo: Ferien-Banner testweise einblenden",
  badge_heute_schulfrei: "Badge: Heute schulfrei",
  badge_morgen_schulfrei: "Badge: Morgen schulfrei",
  badge_heute_feiertag: "Badge: Heute Feiertag",
  badge_morgen_feiertag: "Badge: Morgen Feiertag",
  show_strip: "Tages-Streifen anzeigen",
  strip_days: "Tage im Streifen",
  show_feiertag: "Feiertage in der Terminliste",
  show_ferien: "Schulferien in der Terminliste",
  termine_anzahl: "Termine in der Liste (ab Add-on v1.4.0)",
};

class SchulferienCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...DEFAULTS, ...config };
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  _update() {
    if (!this._hass || !this._config) return;

    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => EDITOR_LABELS[s.name] || s.name;
      this._form.addEventListener("value-changed", (ev) => {
        const v = ev.detail.value || {};
        const [prefix, suffix = ""] = String(v.region || "").split("|");
        const config = { type: "custom:schulferien-card", prefix: prefix || this._config.prefix };
        if (suffix) config.suffix = suffix;
        if (v.title) config.title = v.title;
        if (v.show_banner === false) config.show_banner = false;
        if (v.demo_banner === true) config.demo_banner = true;
        if (v.badge_heute_schulfrei === false) config.badge_heute_schulfrei = false;
        if (v.badge_morgen_schulfrei === false) config.badge_morgen_schulfrei = false;
        if (v.badge_heute_feiertag === false) config.badge_heute_feiertag = false;
        if (v.badge_morgen_feiertag === false) config.badge_morgen_feiertag = false;
        if (v.show_strip === false) config.show_strip = false;
        if (v.show_feiertag === false) config.show_feiertag = false;
        if (v.show_ferien === false) config.show_ferien = false;
        if (v.strip_days && Number(v.strip_days) !== 14) config.strip_days = Number(v.strip_days);
        if (v.termine_anzahl && Number(v.termine_anzahl) !== 4) config.termine_anzahl = Number(v.termine_anzahl);
        this._config = { ...DEFAULTS, ...config };
        this.dispatchEvent(new CustomEvent("config-changed",
          { detail: { config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }

    const regions = detectRegions(this._hass);
    const options = regions.map((r) => ({
      value: `${r.prefix}|${r.suffix}`,
      label: r.prefix.replace(/^(schulferien|feiertage)_/, (m, p) =>
        (p === "feiertage" ? "Feiertage: " : "Schulferien: ")) + (r.suffix ? ` (Suffix: ${r.suffix})` : ""),
    }));
    const current = `${this._config.prefix || ""}|${this._config.suffix || ""}`;
    if (this._config.prefix && !options.some((o) => o.value === current)) {
      options.push({ value: current, label: `${this._config.prefix} (Entitäten nicht gefunden)` });
    }

    this._form.hass = this._hass;
    this._form.schema = [
      { name: "region", selector: { select: { mode: "dropdown", options } } },
      { name: "title", selector: { text: {} } },
      { name: "show_banner", selector: { boolean: {} } },
      { name: "demo_banner", selector: { boolean: {} } },
      { name: "", type: "grid", schema: [
        { name: "badge_heute_schulfrei", selector: { boolean: {} } },
        { name: "badge_morgen_schulfrei", selector: { boolean: {} } },
        { name: "badge_heute_feiertag", selector: { boolean: {} } },
        { name: "badge_morgen_feiertag", selector: { boolean: {} } },
      ] },
      { name: "show_strip", selector: { boolean: {} } },
      { name: "strip_days", selector: { number: { min: 3, max: 14, step: 1, mode: "slider" } } },
      { name: "show_feiertag", selector: { boolean: {} } },
      { name: "show_ferien", selector: { boolean: {} } },
      { name: "termine_anzahl", selector: { number: { min: 1, max: 12, step: 1, mode: "slider" } } },
    ];
    this._form.data = {
      region: current,
      title: this._config.title || "",
      show_banner: this._config.show_banner !== false,
      demo_banner: this._config.demo_banner === true,
      badge_heute_schulfrei: this._config.badge_heute_schulfrei !== false,
      badge_morgen_schulfrei: this._config.badge_morgen_schulfrei !== false,
      badge_heute_feiertag: this._config.badge_heute_feiertag !== false,
      badge_morgen_feiertag: this._config.badge_morgen_feiertag !== false,
      show_strip: this._config.show_strip !== false,
      strip_days: Number(this._config.strip_days) || 14,
      show_feiertag: this._config.show_feiertag !== false,
      show_ferien: this._config.show_ferien !== false,
      termine_anzahl: Number(this._config.termine_anzahl) || 4,
    };
  }
}

if (customElements.get("schulferien-card")) {
  console.warn(`SCHULFERIEN-CARD v${CARD_VERSION} nicht geladen - die Karte ist bereits registriert. `
    + "Vermutlich ist sie doppelt eingebunden (z. B. über HACS und über das Add-on).");
} else {
  customElements.define("schulferien-card", SchulferienCard);
  customElements.define("schulferien-card-editor", SchulferienCardEditor);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "schulferien-card",
    name: "Schulferien Card",
    description: "Status, Tages-Vorschau und Terminliste des Schulferien & Feiertage Managers",
    preview: true,
  });
}
