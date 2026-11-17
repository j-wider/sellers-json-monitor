(function () {
  "use strict";
  // Reiter Vermarkter, Website-Suche und Marktkennzahlen. Die Daten (YYYY-MM-adstxt.json) werden erst
  // beim ersten Öffnen eines dieser Reiter geladen, damit die Übersicht schnell bleibt.
  const DATA_DIR = location.pathname.includes("/site/") ? "../data/aggregates/" : "data/aggregates/";
  const TABS = ["uebersicht", "vermarkter", "suche", "markt"];
  const PATHS = [
    ["selbst", "selbst verkauft", "var(--role-pub)"],
    ["vermarkter", "über Vermarkter", "var(--role-both)"],
    ["reseller", "über Reseller", "var(--role-int)"],
    ["google", "über Google-Bidding", "var(--role-google)"],
    ["unbekannt", "Seller-ID unbekannt", "var(--role-nd)"],
  ];
  const PATH_LABEL = Object.fromEntries(PATHS.map(([k, l]) => [k, l]));
  const EINST = { werbung: "Werbe-Website", keine_werbung: "keine Werbung", nicht_abrufbar: "nicht abrufbar" };
  const STATUS = {
    gefunden: "ads.txt gefunden, aber ohne gültige Zeile oder mit der Platzhalter-Zeile für Websites ohne Werbung.",
    keine_adstxt: "Keine ads.txt (HTTP 404 oder leere Datei).",
    fehlerseite: "Unter /ads.txt liefert der Server eine HTML-Seite statt einer Textdatei.",
    blockiert: "Der Server hat den Abruf abgelehnt (HTTP 401, 403 oder 429).",
    zeitueberschreitung: "Der Server hat nicht innerhalb von 10 Sekunden geantwortet.",
    fehler: "Der Abruf ist fehlgeschlagen (Verbindungsfehler, Serverfehler oder unzulässige Weiterleitung).",
  };
  const CONF = "vertraulich";
  const fmt = new Intl.NumberFormat("de-DE");
  const pct = (x) => (x * 100).toLocaleString("de-DE", { maximumFractionDigits: 1 }) + " %";
  const num = (x) => x.toLocaleString("de-DE", { maximumFractionDigits: 1 });
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const $ = (id) => document.getElementById(id);
  const tier = (r) => (r <= 1000 ? "Top 1.000" : r <= 5000 ? "Top 5.000" : "Top 10.000");
  const monthName = (y, m) => new Date(+y, +m - 1, 1).toLocaleDateString("de-DE", { month: "long", year: "numeric" });

  const st = { month: null, data: undefined, ssps: [], loading: null, sort: "sites", desc: true, filter: "", all: false, sel: null, tier: "10000", site: "" };

  /* ---------- Reiter ---------- */
  const tabBtns = [...document.querySelectorAll('[role="tab"]')];
  tabBtns.forEach((b, i) => {
    b.addEventListener("click", () => go(b.dataset.tab));
    b.addEventListener("keydown", (e) => {
      const k = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabBtns.length - 1 }[e.key];
      if (k === undefined) return;
      e.preventDefault();
      const t = tabBtns[(k + tabBtns.length) % tabBtns.length];
      t.focus();
      go(t.dataset.tab);
    });
  });
  function go(tab, site) {
    const h = tab === "uebersicht" ? "" : "#" + tab + (site ? "/" + site : "");
    if (location.hash !== h) history.pushState(null, "", h || location.pathname + location.search);
    route();
  }
  function route() {
    const [tab, site] = location.hash.slice(1).split("/");
    const t = TABS.includes(tab) ? tab : "uebersicht";
    if (site) st.site = decodeURIComponent(site);
    tabBtns.forEach((b) => {
      const on = b.dataset.tab === t;
      b.setAttribute("aria-selected", on);
      b.tabIndex = on ? 0 : -1;
    });
    TABS.forEach((x) => ($("p-" + x).hidden = x !== t));
    if (t !== "uebersicht") show(t);
  }
  window.addEventListener("hashchange", route);
  $("month").addEventListener("change", () => {
    st.data = undefined;
    st.sel = null;
    const t = location.hash.slice(1).split("/")[0];
    if (TABS.includes(t) && t !== "uebersicht") show(t);
  });
  route();

  /* ---------- Daten ---------- */
  async function currentMonth() {
    if ($("month").value) return $("month").value;
    const months = await (await fetch(DATA_DIR + "index.json")).json();
    return months[months.length - 1];
  }
  async function load() {
    const m = await currentMonth();
    if (st.data !== undefined && st.month === m) return;
    if (st.loading) return st.loading;
    st.loading = (async () => {
      const [a, b] = await Promise.all([fetch(DATA_DIR + m + "-adstxt.json"), fetch(DATA_DIR + m + ".json")]);
      st.ssps = b.ok ? (await b.json()).ssps : [];
      st.data = a.ok ? await a.json() : null;
      st.month = m;
    })();
    try { await st.loading; } finally { st.loading = null; }
  }
  async function show(tab) {
    const el = $("p-" + tab);
    if (st.data === undefined) el.innerHTML = `<section class="panel"><p class="empty">Daten werden geladen.</p></section>`;
    try {
      await load();
    } catch (e) {
      el.innerHTML = `<section class="panel"><p class="empty">Die ads.txt-Daten konnten nicht geladen werden (${esc(e.message)}).</p></section>`;
      return;
    }
    if (!st.data) {
      el.innerHTML = `<section class="panel"><h2>${title(tab)}</h2><p class="empty">Für diesen Monat liegen keine ads.txt-Daten vor. Der Abgleich ist seit November 2026 Teil des Monatslaufs.</p></section>`;
      return;
    }
    ({ vermarkter: renderVermarkter, suche: renderSuche, markt: renderMarkt })[tab](el);
  }
  const title = (tab) => ({ vermarkter: "Vermarkter-Portfolio", suche: "Website-Suche", markt: "Marktkennzahlen" })[tab];
  const sspById = (id) => st.ssps.find((s) => s.id === id) || { id, name: id, short: id.slice(0, 2).toUpperCase(), color: "#6b7a9c" };
  const sspOrder = (id) => { const i = st.ssps.findIndex((s) => s.id === id); return i < 0 ? 99 : i; };

  function source() {
    const d = st.data, c = d.counts;
    const crux = monthName(d.crux_month.slice(0, 4), d.crux_month.slice(4));
    const day = new Date(d.fetched_at).toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" });
    return `<p class="ax-src">Startliste: Chrome-UX-Report Deutschland, ${crux}, alle Websites bis Rangstufe 10.000.
      ads.txt abgerufen am ${day}. ${fmt.format(c.domains)} Websites, davon ${fmt.format(c.nicht_abrufbar)} nicht abrufbar.
      ${fmt.format(c.adult_removed)} Erwachsenenseiten wurden vorab entfernt.
      <span>Quellen: <a href="https://github.com/zakird/crux-top-lists" target="_blank" rel="noopener">CrUX-Toplisten</a>,
      Erwachsenenfilter <a href="https://github.com/olbat/ut1-blacklists" target="_blank" rel="noopener">UT1, Universität Toulouse Capitole</a> (CC BY-SA 4.0).</span></p>`;
  }

  /* ---------- Vermarkter ---------- */
  function renderVermarkter(el) {
    el.innerHTML = `<section class="panel" aria-labelledby="vm-h">
        <h2 id="vm-h">Vermarkter-Portfolio</h2>
        <p>Vermarkter einer Website ist der Inhaber der Konten, die in ihrer ads.txt als DIRECT stehen, laut sellers.json aber einer anderen Domain gehören. Gruppiert wird nach dieser Domain, Häuser mit mehreren Domains sind zusammengefasst.</p>
        ${source()}
        <div class="field"><label for="vm-q">Vermarkter filtern</label><input id="vm-q" type="search" autocomplete="off" value="${esc(st.filter)}"></div>
        <div class="tscroll"><table class="vmt"><thead><tr>
          ${th("name", "Vermarkter")}${th("sites", "Websites")}${th("top1000", "davon Top 1.000")}<th>SSPs</th>
        </tr></thead><tbody id="vm-body"></tbody></table></div>
        <p id="vm-more"></p>
      </section>
      <section class="panel" id="vm-detail" aria-live="polite" hidden></section>`;
    $("vm-q").addEventListener("input", (e) => { st.filter = e.target.value; vmRows(); });
    el.querySelectorAll("th button").forEach((b) => b.addEventListener("click", () => {
      st.desc = st.sort === b.dataset.k ? !st.desc : b.dataset.k !== "name";
      st.sort = b.dataset.k;
      renderVermarkter(el);
    }));
    vmRows();
    vmDetail();
  }
  function th(k, label) {
    const sort = st.sort === k ? (st.desc ? "descending" : "ascending") : "none";
    return `<th aria-sort="${sort}"><button type="button" class="sortbtn" data-k="${k}">${label}</button></th>`;
  }
  function vmRows() {
    const q = st.filter.trim().toLowerCase();
    let list = st.data.vermarkter.filter((v) => !q || v.name.toLowerCase().includes(q) || v.domains.some((d) => d.includes(q)));
    const dir = st.desc ? -1 : 1;
    list.sort((a, b) => (a.id === CONF) - (b.id === CONF) ||
      (st.sort === "name" ? dir * a.name.localeCompare(b.name, "de") : dir * (a[st.sort] - b[st.sort])) || a.name.localeCompare(b.name, "de"));
    const shown = st.all || q ? list : list.slice(0, 30);
    $("vm-body").innerHTML = shown.map((v) => `<tr${v.id === st.sel ? ' class="on"' : ""}>
        <td><button type="button" class="linkbtn" data-id="${esc(v.id)}">${esc(v.name)}</button>
          <span class="sub">${v.id === CONF ? "Konten ohne Domain in der sellers.json" : esc(v.domains.join(", "))}</span></td>
        <td>${fmt.format(v.sites)}</td><td>${fmt.format(v.top1000)}</td>
        <td><span class="sq-row">${Object.keys(v.ssps).sort((a, b) => sspOrder(a) - sspOrder(b)).map((s) => sq(s, `${sspById(s).name}: ${fmt.format(v.ssps[s])} Websites`)).join("")}</span></td></tr>`).join("")
      || `<tr><td colspan="4" class="empty">Kein Vermarkter passt zum Filter.</td></tr>`;
    $("vm-body").querySelectorAll(".linkbtn").forEach((b) => b.addEventListener("click", () => {
      st.sel = b.dataset.id;
      vmRows();
      vmDetail();
      $("vm-detail").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    }));
    const more = $("vm-more");
    more.innerHTML = shown.length < list.length ? `<button type="button" class="chip tool" id="vm-all">Alle ${fmt.format(list.length)} anzeigen</button>` : "";
    if ($("vm-all")) $("vm-all").addEventListener("click", () => { st.all = true; vmRows(); });
  }
  function sq(id, tip) {
    const s = sspById(id);
    return `<span class="sq" style="--c:${s.color}" title="${esc(tip)}">${esc(s.short || s.name)}</span>`;
  }
  function vmDetail() {
    const box = $("vm-detail");
    const v = st.data.vermarkter.find((x) => x.id === st.sel);
    box.hidden = !v;
    if (!v) return;
    const groups = ["Top 1.000", "Top 5.000", "Top 10.000"].map((t) => [t, v.site_list.filter(([, r]) => tier(r) === t)]).filter(([, l]) => l.length);
    box.innerHTML = `<h2>${esc(v.name)}</h2>
      <p>${v.id === CONF ? "Konten, die in der sellers.json als vertraulich markiert sind und keine Domain nennen. Sie lassen sich keinem Haus zuordnen." : "Domains laut sellers.json: " + esc(v.domains.join(", "))}</p>
      <div class="kv"><div><b>${fmt.format(v.sites)}</b><span>Websites</span></div><div><b>${fmt.format(v.top1000)}</b><span>davon Top 1.000</span></div><div><b>${Object.keys(v.ssps).length}</b><span>SSPs</span></div></div>
      <h3>Über welche SSPs</h3>
      <p class="note">Strichstärke: Zahl der Websites, deren ads.txt ein DIRECT-Konto des Vermarkters bei dieser SSP nennt. Eine Website kann bei mehreren SSPs zählen.</p>
      <div class="vm-sankey"><svg id="vm-svg" role="img" aria-label="Sankey-Diagramm: ${esc(v.name)} zu den SSPs"></svg></div>
      <h3>Websites</h3>
      ${groups.map(([t, l]) => `<div class="sitegroup"><h4>${t} <span>${fmt.format(l.length)}</span></h4><ul class="sitelist">${l.map(([d]) => `<li><a href="#suche/${encodeURIComponent(d)}">${esc(d)}</a></li>`).join("")}</ul></div>`).join("")}`;
    drawSankey(v);
  }
  function drawSankey(v) {
    const svg = d3.select("#vm-svg");
    const ids = Object.keys(v.ssps).sort((a, b) => sspOrder(a) - sspOrder(b));
    const W = svg.node().getBoundingClientRect().width || 600;
    const H = Math.max(160, ids.length * 46);
    svg.attr("viewBox", `0 0 ${W} ${H}`).attr("height", H);
    const nodes = [{ id: "v", name: v.name }, ...ids.map((s) => ({ id: s, name: sspById(s).name }))];
    const links = ids.map((s) => ({ source: "v", target: s, value: v.ssps[s] }));
    const g = d3.sankey().nodeId((d) => d.id).nodeWidth(12).nodePadding(14).nodeSort(null)
      .extent([[4, 6], [W - 150, H - 6]])({ nodes: nodes.map((d) => ({ ...d })), links });
    svg.selectAll("*").remove();
    svg.append("g").selectAll("path").data(g.links).join("path").attr("class", "link")
      .attr("d", d3.sankeyLinkHorizontal()).attr("stroke", (d) => sspById(d.target.id).color)
      .attr("stroke-opacity", 0.55).attr("stroke-width", (d) => Math.max(1.5, d.width))
      .append("title").text((d) => `${d.target.name}: ${fmt.format(d.value)} Websites`);
    svg.append("g").selectAll("rect").data(g.nodes).join("rect")
      .attr("x", (d) => d.x0).attr("y", (d) => d.y0).attr("width", (d) => d.x1 - d.x0).attr("height", (d) => Math.max(2, d.y1 - d.y0))
      .attr("fill", (d) => (d.id === "v" ? "var(--flow-node)" : sspById(d.id).color));
    svg.append("g").selectAll("text").data(g.nodes.filter((d) => d.id !== "v")).join("text")
      .attr("x", (d) => d.x1 + 8).attr("y", (d) => (d.y0 + d.y1) / 2).attr("dy", "0.35em")
      .text((d) => `${d.name}  ${fmt.format(d.value)}`);
  }

  /* ---------- Website-Suche ---------- */
  function renderSuche(el) {
    el.innerHTML = `<section class="panel" aria-labelledby="s-h">
        <h2 id="s-h">Website-Suche</h2>
        <p>Zeigt für eine Website der Startliste, welche Konten ihre ads.txt bei den sechs SSPs nennt und wem diese Konten laut sellers.json gehören.</p>
        ${source()}
        <div class="field"><label for="s-q">Website</label><input id="s-q" type="search" list="s-list" autocomplete="off" spellcheck="false" placeholder="zum Beispiel spiegel.de"></div>
        <datalist id="s-list">${st.data.sites.map((s) => `<option value="${s.d}">`).join("")}</datalist>
      </section>
      <section class="panel" id="s-out" aria-live="polite" hidden></section>`;
    const q = $("s-q");
    const norm = (x) => x.trim().toLowerCase().replace(/^[a-z]+:\/\//, "").replace(/[/?#].*$/, "").replace(/^www\./, "").replace(/\.$/, "");
    const find = (x) => st.data.sites.find((s) => s.d === norm(x));
    q.addEventListener("input", () => { if (find(q.value)) siteOut(find(q.value)); });
    q.addEventListener("change", () => {
      const s = find(q.value);
      if (s) { if (location.hash !== "#suche/" + s.d) history.replaceState(null, "", "#suche/" + s.d); siteOut(s); }
      else if (q.value.trim()) siteOut(null, norm(q.value));
    });
    if (st.site) { q.value = st.site; const s = find(st.site); s ? siteOut(s) : siteOut(null, norm(st.site)); }
  }
  // Die einzelnen ads.txt-Zeilen liegen in Teildateien nach Anfangsbuchstabe der Domain.
  const shards = {};
  async function siteRows(d) {
    const k = /^[a-z0-9]/.test(d) ? d[0] : "_";
    const key = st.month + "/" + k;
    if (!shards[key]) shards[key] = fetch(`${DATA_DIR}${st.month}-adstxt/${k}.json`).then((r) => (r.ok ? r.json() : { names: {}, sites: {} }));
    const sh = await shards[key], f = st.data.row_format;
    return (sh.sites[d] || []).map(([si, sid, pi, r]) => [f.ssps[si], sid, sh.names[si + ":" + sid] || "", f.paths[pi], r ? "RESELLER" : "DIRECT"]);
  }
  async function siteOut(s, query) {
    const out = $("s-out");
    out.hidden = false;
    if (!s) { out.innerHTML = `<p class="empty">${esc(query)} steht nicht in der Startliste (Rangstufen bis 10.000 laut CrUX). Erwachsenenseiten sind entfernt.</p>`; return; }
    st.site = s.d;
    if (s.e === "werbung") {
      out.innerHTML = `<h2>${esc(s.d)}</h2><p class="empty">Zeilen werden geladen.</p>`;
      try { s = { ...s, rows: await siteRows(s.d) }; } catch (e) { out.innerHTML = `<p class="empty">Die Zeilen konnten nicht geladen werden (${esc(e.message)}).</p>`; return; }
      if (st.site !== s.d) return; // inzwischen wurde eine andere Website gewählt
    } else s = { ...s, rows: [] };
    const vm = Object.fromEntries(st.data.vermarkter.map((v) => [v.id, v]));
    const vNames = s.v.map((id) => (vm[id] ? vm[id].name : id));
    const mgr = s.mgr ? s.mgr.split("|") : [];
    const vDomains = new Set(s.v.flatMap((id) => (vm[id] ? vm[id].domains : [])));
    const differ = mgr.length && s.v.length && !mgr.some((m) => vDomains.has(m.toLowerCase().replace(/^www\./, "")));
    const kv = (v, l) => `<div><b>${v}</b><span>${l}</span></div>`;
    const rows = s.rows.slice().sort((a, b) => sspOrder(a[0]) - sspOrder(b[0]) || PATHS.findIndex((p) => p[0] === a[3]) - PATHS.findIndex((p) => p[0] === b[3]) || a[1].localeCompare(b[1]));
    out.innerHTML = `<h2>${esc(s.d)}</h2>
      <div class="kv">${kv(tier(s.r), "Rangstufe")}${kv(EINST[s.e], "Einstufung")}${s.e === "werbung" ? kv(fmt.format(s.n), "Zeilen in der ads.txt") + kv(fmt.format(s.res), "davon RESELLER") : ""}</div>
      ${s.e !== "werbung" ? `<p>${STATUS[s.s] || ""}</p>` : ""}
      ${s.e === "werbung" ? `<dl class="facts">
        <dt>Vermarkter laut sellers.json</dt><dd>${vNames.length ? esc(vNames.join(", ")) : "keiner"}</dd>
        ${mgr.length ? `<dt>MANAGERDOMAIN in der ads.txt</dt><dd>${esc(mgr.join(", "))}</dd>` : ""}
        ${s.own ? `<dt>OWNERDOMAIN in der ads.txt</dt><dd>${esc(s.own.split("|").join(", "))}</dd>` : ""}
      </dl>
      ${differ ? `<p class="note">MANAGERDOMAIN und der Vermarkter laut sellers.json stimmen nicht überein. Beide Angaben sind aufgeführt.</p>` : ""}
      <h3>Zeilen zu den sechs SSPs</h3>
      ${rows.length ? `<div class="tscroll"><table class="srt"><thead><tr><th>SSP</th><th>Seller-ID</th><th>Verkäufer laut sellers.json</th><th>Verkaufsweg</th><th>Beziehung</th></tr></thead><tbody>
        ${rows.map(([ssp, id, name, path, rel]) => `<tr><td>${sq(ssp, sspById(ssp).name)} ${esc(sspById(ssp).name)}</td><td class="id">${esc(id)}</td><td>${esc(name) || '<span class="dim">nicht angegeben</span>'}</td><td>${PATH_LABEL[path]}</td><td>${rel}</td></tr>`).join("")}
      </tbody></table></div>` : `<p class="note">Die ads.txt nennt keine der sechs SSPs.</p>`}` : ""}`;
  }

  /* ---------- Marktkennzahlen ---------- */
  function renderMarkt(el) {
    const m = st.data.market[st.tier], p = st.data.prev && st.data.prev[st.tier];
    const delta = (a, b, isPct) => (b == null || a == null ? "" : `<div class="d">${a - b >= 0 ? "+" : "−"}${isPct ? num(Math.abs(a - b) * 100) + " Prozentpunkte" : num(Math.abs(a - b))} zum Vormonat</div>`);
    const kpi = (v, l, d) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div>${d}</div>`;
    const ids = Object.keys(m.per_ssp).sort((a, b) => sspOrder(a) - sspOrder(b));
    const max = Math.max(1, ...ids.map((i) => m.per_ssp[i].alle));
    el.innerHTML = `<section class="panel" aria-labelledby="mk-h">
        <h2 id="mk-h">Marktkennzahlen</h2>
        <p>Wie verbreitet ads.txt-Dateien unter den meistgenutzten Websites in Deutschland sind und über welche Wege die sechs SSPs dort vorkommen. Die Zahlen sagen, wer verkaufen darf, nicht wie viel verkauft wird.</p>
        ${source()}
        <div class="fg"><span>Rangstufe</span><div class="chips" role="group" aria-label="Rangstufe">
          ${["1000", "5000", "10000"].map((t) => `<button type="button" class="chip" data-t="${t}" aria-pressed="${t === st.tier}">Top ${fmt.format(+t)}</button>`).join("")}
        </div></div>
      </section>
      <section class="kpis" aria-label="Kennzahlen ads.txt">
        ${kpi(m.share_ads == null ? "-" : pct(m.share_ads), `der abrufbaren Websites haben eine ads.txt mit Werbung (${fmt.format(m.werbung)} von ${fmt.format(m.domains - m.nicht_abrufbar)})`, delta(m.share_ads, p && p.share_ads, true))}
        ${kpi(m.median_lines == null ? "-" : num(m.median_lines), "Zeilen hat die ads.txt einer Werbe-Website im Median", delta(m.median_lines, p && p.median_lines))}
        ${kpi(m.reseller_share == null ? "-" : pct(m.reseller_share), "dieser Zeilen sind RESELLER-Zeilen", delta(m.reseller_share, p && p.reseller_share, true))}
        ${kpi(fmt.format(m.nicht_abrufbar), "Websites waren nicht abrufbar und zählen nicht mit", "")}
      </section>
      <section class="panel" aria-labelledby="mk-s">
        <h2 id="mk-s">Werbe-Websites je SSP nach Verkaufsweg</h2>
        <p>Zahl der Werbe-Websites, deren ads.txt die SSP nennt. Eine Website zählt je SSP einmal, beim direktesten Weg: selbst verkauft vor Vermarkter, Reseller, Google-Bidding und unbekannter Seller-ID.</p>
        <div class="legend">${PATHS.map(([, l, c]) => `<span><i style="background:${c}"></i>${l}</span>`).join("")}</div>
        <div class="orow rhead"><span></span><span></span><span class="onum">Websites</span></div>
        ${ids.map((i) => {
          const c = m.per_ssp[i], s = sspById(i);
          const segs = PATHS.filter(([k]) => c[k]).map(([k, l, col]) => `<span class="seg" style="width:${(c[k] / max) * 100}%;background:${col}" title="${esc(s.name)}, ${l}: ${fmt.format(c[k])} Websites"></span>`).join("");
          return `<div class="orow"><span class="oname"><i style="background:${s.color}"></i>${esc(s.name)}</span><div class="stack">${segs}</div><span class="onum">${fmt.format(c.alle)}</span></div>`;
        }).join("")}
      </section>`;
    el.querySelectorAll("[data-t]").forEach((b) => b.addEventListener("click", () => { st.tier = b.dataset.t; renderMarkt(el); }));
  }
})();
