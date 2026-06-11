/* Schulferien-Card – Lovelace Custom Card für den Schulferien & Feiertage Manager
 *
 * Beispiel-Konfiguration:
 *   type: custom:schulferien-card
 *   title: Schulferien Bayern
 *   prefix: schulferien_bayern      # bzw. feiertage_bayern bei "Nur Feiertage"
 *   suffix: ""                      # optional, falls beim Anlegen ein Suffix vergeben wurde
 *   show_strip: true                # 14-Tage-Streifen anzeigen
 */
class SchulferienCard extends HTMLElement {
  setConfig(config) {
    if (!config.prefix) {
      throw new Error('Bitte "prefix" angeben, z. B. prefix: schulferien_bayern');
    }
    this._config = { show_strip: true, suffix: "", ...config };
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
    return ids.map(([d, k]) => {
      const s = this._st(d, k);
      return s ? [s.state, s.attributes] : null;
    });
  }

  _fmt(iso) {
    if (!iso) return "–";
    return new Date(iso + "T00:00:00").toLocaleDateString("de-DE",
      { day: "2-digit", month: "2-digit", year: "numeric" });
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

    if (!hs && !hf && !combined) {
      this.innerHTML = `<ha-card><div class="sfc-wrap">
        Keine Entitäten mit Präfix <code>${c.prefix}</code> gefunden.<br>
        Präfix/Suffix bitte aus der Infobox „Entitäten" im Add-on übernehmen
        (ohne den Entitätsteil, z. B. <code>schulferien_bayern</code>).</div></ha-card>`;
      return;
    }

    // Daten zusammensetzen – funktioniert für Einzel-, Feiertage- und Kombi-Modus
    const a = combined ? combined.attributes : {};
    const strip = (nf?.attributes.vorschau) || a.vorschau || [];
    const nextFt = nf
      ? { name: nf.state !== "unknown" ? nf.state : null, datum: nf.attributes.datum, in: nf.attributes.in_tagen }
      : { name: a.naechster_feiertag, datum: a.naechster_feiertag_datum, in: a.naechster_feiertag_in_tagen };
    const nextFe = ns
      ? { name: ns.state !== "unknown" ? ns.state : null, beginn: ns.attributes.beginn,
          ende: ns.attributes.ende, in: ns.attributes.in_tagen, aktuell: ns.attributes.aktuell_ferien }
      : { name: a.naechste_schulferien, beginn: a.schulferien_beginn,
          ende: a.schulferien_ende, in: a.schulferien_in_tagen, aktuell: a.aktuell_ferien };

    const badges = combined
      ? `<div class="badge ${["Ferien","Feiertag","Wochenende"].includes(combined.state) ? "on" : ""}">
           Heute: <b>${combined.state}</b></div>`
      : [this._badge("Heute schulfrei", hs, false), this._badge("Morgen schulfrei", ms, false),
         this._badge("Heute Feiertag", hf, true), this._badge("Morgen Feiertag", mf, true)].join("");

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

    const rows = [];
    if (nextFe.aktuell) rows.push(`<div class="row live"><span class="ico">🏖️</span>
      <span class="nm">${nextFe.aktuell}</span><span class="when">läuft gerade</span></div>`);
    if (nextFt.name) rows.push(`<div class="row"><span class="ico">★</span>
      <span class="nm">${nextFt.name} <small>${this._fmt(nextFt.datum)}</small></span>
      <span class="when">${this._in(nextFt.in)}</span></div>`);
    if (nextFe.name) rows.push(`<div class="row"><span class="ico">🏖️</span>
      <span class="nm">${nextFe.name} <small>${this._fmt(nextFe.beginn)} – ${this._fmt(nextFe.ende)}</small></span>
      <span class="when">${this._in(nextFe.in)}</span></div>`);

    this.innerHTML = `
      <ha-card ${c.title ? `header="${c.title}"` : ""}>
        <div class="sfc-wrap">
          <div class="badges">${badges}</div>
          ${stripHtml}
          <div class="rows">${rows.join("") || "<small>Keine anstehenden Termine.</small>"}</div>
        </div>
      </ha-card>
      <style>
        .sfc-wrap{padding:0 16px 16px}
        ha-card:not([header]) .sfc-wrap{padding-top:16px}
        .badges{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
        .badge{font-size:.8rem;border-radius:8px;padding:4px 10px;
          background:var(--secondary-background-color);color:var(--secondary-text-color);
          border:1px solid var(--divider-color)}
        .badge.on{color:var(--success-color,#4cc38a);border-color:var(--success-color,#4cc38a);
          background:rgba(76,195,138,.12)}
        .badge.on.ft{color:#7aa2ff;border-color:#7aa2ff;background:rgba(122,162,255,.12)}
        .strip{display:flex;gap:3px}
        .strip .d{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;
          font-size:.62rem;line-height:1.15;text-align:center;color:var(--secondary-text-color);min-width:0}
        .strip .box{width:100%;height:20px;border-radius:5px;
          background:var(--secondary-background-color);border:1px solid var(--divider-color)}
        .strip .d.today .box{outline:2px solid var(--primary-text-color);outline-offset:1px}
        .strip .d.ferien .box{background:rgba(232,162,61,.55);border-color:#e8a23d}
        .strip .d.feiertag .box{background:rgba(122,162,255,.6);border-color:#7aa2ff}
        .strip .d.wochenende .box{background:rgba(138,148,163,.25)}
        .legend{display:flex;gap:12px;font-size:.68rem;color:var(--secondary-text-color);margin:7px 0 12px}
        .legend i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:4px}
        .lg-ferien{background:#e8a23d}.lg-feiertag{background:#7aa2ff}.lg-we{background:rgba(138,148,163,.45)}
        .rows{display:flex;flex-direction:column;gap:6px}
        .row{display:flex;gap:8px;align-items:baseline;font-size:.9rem}
        .row .ico{width:18px;text-align:center;flex:none}
        .row .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .row .nm small{color:var(--secondary-text-color)}
        .row .when{margin-left:auto;color:var(--secondary-text-color);white-space:nowrap;font-size:.82rem}
        .row.live .nm{color:var(--success-color,#4cc38a)}
      </style>`;
  }

  getCardSize() { return 4; }

  static getStubConfig() {
    return { prefix: "schulferien_bayern", title: "Schulferien", show_strip: true };
  }
}

customElements.define("schulferien-card", SchulferienCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "schulferien-card",
  name: "Schulferien Card",
  description: "Status, 14-Tage-Vorschau und nächste Termine des Schulferien & Feiertage Managers",
});
