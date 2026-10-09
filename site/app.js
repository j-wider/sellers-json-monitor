(function () {
  "use strict";
  // Lokal läuft die Seite unter /site/, veröffentlicht liegt sie im Wurzelverzeichnis.
  const DATA_DIR = location.pathname.includes("/site/") ? "../data/aggregates/" : "data/aggregates/";
  let SSP_COLOR = {};
  const TYPE_LABEL = { PUBLISHER: "Publisher", INTERMEDIARY: "Intermediary", BOTH: "Beides", NICHT_ANGEGEBEN: "Typ nicht angegeben" };
  const TYPE_ORDER = ["PUBLISHER", "INTERMEDIARY", "BOTH", "NICHT_ANGEGEBEN"];
  const FOCUS = ["de", "at", "ch"];
  const NO_DOMAIN = "unbekannt";
  const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const isDark = () => document.documentElement.dataset.theme !== "light";
  const fmt = new Intl.NumberFormat("de-DE");
  const pct = (x) => (x * 100).toLocaleString("de-DE", { maximumFractionDigits: 1 }) + " %";
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const $ = (id) => document.getElementById(id);

  const state = { data: null, groupOf: null, groups: [], ssp: new Set(), extra: new Set() };
  let anim = null;

  init().catch((e) => {
    document.querySelector("main").innerHTML =
      '<p class="empty">Daten konnten nicht geladen werden. Läuft der lokale Server im Projektordner? (' + e.message + ")</p>";
  });

  async function init() {
    const months = await (await fetch(DATA_DIR + "index.json")).json();
    const sel = $("month");
    sel.innerHTML = months.slice().reverse().map((m) => `<option value="${m}">${monthLabel(m)}</option>`).join("");
    sel.addEventListener("change", () => loadMonth(sel.value));
    let t;
    new ResizeObserver(() => { clearTimeout(t); t = setTimeout(renderFlow, 120); }).observe($("chart"));
    reduceMotion.addEventListener("change", renderFlow);
    const themeBtn = $("theme");
    const label = () => {
      const dark = isDark();
      themeBtn.textContent = dark ? "Hell" : "Dunkel";
      themeBtn.setAttribute("aria-label", dark ? "Zum hellen Design wechseln" : "Zum dunklen Design wechseln");
    };
    themeBtn.addEventListener("click", () => {
      const next = isDark() ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) { /* ohne Speicher weiter */ }
      label();
      if (state.data) renderFlow();
    });
    label();
    await loadMonth(months[months.length - 1]);
  }

  function monthLabel(m) {
    const [y, mo] = m.split("-");
    return new Date(+y, +mo - 1, 1).toLocaleDateString("de-DE", { month: "long", year: "numeric" });
  }

  async function loadMonth(m) {
    const res = await fetch(DATA_DIR + m + ".json");
    if (!res.ok) throw new Error("HTTP " + res.status);
    state.data = await res.json();
    SSP_COLOR = Object.fromEntries(state.data.ssps.map((s) => [s.id, s.color || "#6b7a9c"]));
    state.ssp = new Set(state.data.ssps.map((x) => x.id));
    state.extra = new Set();
    buildGroups();
    renderFilters();
    renderAll();
  }

  // Länderendungen: .de/.at/.ch immer einzeln, dazu die häufigsten weiteren, der Rest als "Sonstige".
  function buildGroups() {
    const tot = {};
    state.data.cube.forEach((r) => (tot[r.tld] = (tot[r.tld] || 0) + r.n));
    const others = Object.keys(tot)
      .filter((t) => !FOCUS.includes(t) && t !== NO_DOMAIN)
      .sort((a, b) => tot[b] - tot[a])
      .slice(0, 7);
    const keep = new Set([...FOCUS.filter((t) => tot[t]), ...others]);
    state.groupOf = (t) => (t === NO_DOMAIN ? NO_DOMAIN : keep.has(t) ? t : "sonstige");
    state.groups = [...FOCUS.filter((t) => tot[t]), ...others, "sonstige", ...(tot[NO_DOMAIN] ? [NO_DOMAIN] : [])];
  }
  const groupLabel = (g) => (g === "sonstige" ? "Sonstige" : g === NO_DOMAIN ? "ohne Domain" : "." + g);

  // Standardmäßig ohne die Einträge, die Google als Zwischenstation führen (Intermediary mit Domain google.com).
  // Sie stehen im Bereich "Rollenverhältnis" und würden hier fast vollständig in .com münden.
  const isGoogleWay = (r) => r.type === "INTERMEDIARY" && r.g;

  function filtered() {
    return state.data.cube.filter((r) => state.ssp.has(r.ssp) && (state.extra.has("google") || !isGoogleWay(r)));
  }

  /* ---------- Filter ---------- */
  function chipGroup(label, items, set) {
    const wrap = document.createElement("div");
    wrap.className = "fg";
    wrap.innerHTML = `<span>${label}</span>`;
    const c = document.createElement("div");
    c.className = "chips";
    items.forEach((it) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.textContent = it.label;
      if (it.color) b.style.setProperty("--c", it.color);
      b.setAttribute("aria-pressed", set.has(it.id));
      b.addEventListener("click", () => {
        set.has(it.id) ? set.delete(it.id) : set.add(it.id);
        b.setAttribute("aria-pressed", set.has(it.id));
        renderNote();
        renderFlow();
      });
      c.appendChild(b);
    });
    wrap.appendChild(c);
    return wrap;
  }
  function renderFilters() {
    const box = $("filters");
    box.innerHTML = "";
    const sspGroup = chipGroup("SSP", state.data.ssps.map((s) => ({ id: s.id, label: s.name, color: SSP_COLOR[s.id] })), state.ssp);
    const tool = (text, all) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip tool";
      b.textContent = text;
      b.addEventListener("click", () => {
        state.ssp = all ? new Set(state.data.ssps.map((s) => s.id)) : new Set();
        renderFilters();
        renderNote();
        renderFlow();
      });
      return b;
    };
    sspGroup.querySelector(".chips").append(tool("Alle anwählen", true), tool("Alle abwählen", false));
    box.appendChild(sspGroup);
    box.appendChild(chipGroup("Zusätzlich", [{ id: "google", label: "Intermediary über google.com einblenden" }], state.extra));
  }

  function renderAll() {
    renderHead();
    renderNote();
    renderFlow();
    renderRoles();
    renderOverlap();
    renderDe();
    renderChanges();
    renderQuality();
    renderMethod();
  }

  function renderHead() {
    const d = state.data;
    const days = d.ssps.map((x) => x.fetched_at).filter(Boolean).map((x) => new Date(x)).sort((p, q) => p - q);
    const day = (x) => x.toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" });
    const from = days[0], to = days[days.length - 1];
    const sameMonth = from.getMonth() === to.getMonth() && from.getFullYear() === to.getFullYear();
    const when = day(from) === day(to) ? "am " + day(from) : sameMonth ? "am " + from.getDate() + ". und " + day(to) : "vom " + day(from) + " bis " + day(to);
    $("stand").textContent = days.length ? `${d.ssps.length} SSP-Dateien, abgerufen ${when}` : `${d.ssps.length} SSP-Dateien, ${monthLabel(d.month)}`;
    $("month-wrap").hidden = $("month").options.length < 2;

    const total = d3.sum(d.cube, (r) => r.n);
    const inter = d3.sum(d.cube.filter((r) => r.type === "INTERMEDIARY"), (r) => r.n);
    const interG = d3.sum(d.cube.filter((r) => r.type === "INTERMEDIARY" && r.g), (r) => r.n);
    const t = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
    $("kpis").innerHTML =
      t(fmt.format(total), "Seller-Einträge in allen Dateien") +
      t(fmt.format(d.overlap.unique_domains), "eindeutige Domains dahinter") +
      t(pct(inter / total), `der Einträge sind Intermediary, davon ${pct(interG / inter)} über google.com`) +
      t(pct(d.analysis.direct.domains ? (d.analysis.direct.domains - d.analysis.direct.by_count["1"]) / d.analysis.direct.domains : 0), "der direkt gelisteten Publisher stehen bei mehr als einer SSP");
  }

  function renderNote() {
    const gn = $("gnote");
    if (state.extra.has("google")) { gn.hidden = true; return; }
    const n = d3.sum(state.data.cube.filter((r) => state.ssp.has(r.ssp) && isGoogleWay(r)), (r) => r.n);
    gn.hidden = !n;
    gn.textContent = `Nicht enthalten: ${fmt.format(n)} Einträge, die Google als Zwischenstation führen (Intermediary mit Domain google.com, Exchange Bidding oder Open Bidding). Sie stehen unter „Rollenverhältnis je SSP“.`;
  }

  /* ---------- Sankey + Partikel ---------- */
  function sankeyData(rows) {
    const nodes = new Map();
    const links = new Map();
    const node = (id, label, color, order, ssp) => { if (!nodes.has(id)) nodes.set(id, { id, label, color, order, ssp }); };
    const link = (a, b, v, ssp, tld) => {
      const k = a + ">" + b;
      const l = links.get(k) || { source: a, target: b, value: 0, ssp, tld };
      l.value += v;
      links.set(k, l);
    };
    const sspIdx = Object.fromEntries(state.data.ssps.map((s, i) => [s.id, i]));
    rows.forEach((r) => {
      const g = state.groupOf(r.tld);
      node("s:" + r.ssp, state.data.ssps[sspIdx[r.ssp]].name, SSP_COLOR[r.ssp], sspIdx[r.ssp], r.ssp);
      node("t:" + r.type, TYPE_LABEL[r.type], null, TYPE_ORDER.indexOf(r.type));
      node("l:" + g, groupLabel(g), null, state.groups.indexOf(g));
      link("s:" + r.ssp, "t:" + r.type, r.n, r.ssp);
      link("t:" + r.type, "l:" + g, r.n, null, g);
    });
    return { nodes: [...nodes.values()], links: [...links.values()] };
  }

  function renderFlow() {
    if (!state.data) return;
    const rows = filtered();
    const total = d3.sum(rows, (r) => r.n);
    $("empty").hidden = total > 0;
    const chart = $("chart");
    const svg = d3.select("#sankey");
    svg.selectAll("*").remove();
    clearInterval(anim);
    const W = chart.clientWidth, H = chart.clientHeight;
    const cv = $("particles");
    const dpr = window.devicePixelRatio || 1;
    cv.width = W * dpr;
    cv.height = H * dpr;
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    if (!total) return;

    svg.attr("viewBox", `0 0 ${W} ${H}`);
    const { nodes, links } = sankeyData(rows);
    const labelPad = Math.min(110, W * 0.16);
    const leftPad = Math.min(130, W * 0.18);
    const layout = d3.sankey().nodeId((d) => d.id).nodeWidth(12).nodePadding(10).nodeAlign(d3.sankeyLeft)
      .nodeSort((a, b) => a.order - b.order)
      .extent([[leftPad, 28], [W - 8 - labelPad, H - 8]]);
    const g = layout({ nodes: nodes.map((d) => ({ ...d })), links: links.map((d) => ({ ...d })) });

    [["SSP", 0], ["Rolle", 1], ["Länderendung", 2]].forEach(([t, col]) => {
      const n = g.nodes.find((x) => x.depth === col);
      if (n) svg.append("text").attr("class", "sub").attr("x", n.x0).attr("y", 16).text(t);
    });

    const path = d3.sankeyLinkHorizontal();
    const lg = svg.append("g");
    const isFocus = (l) => !l.ssp && FOCUS.includes(l.tld);
    const nodeCol = cssVar("--flow-node"), grayCol = cssVar("--flow-gray"), focusCol = cssVar("--flow-focus");
    g.links.forEach((l) => {
      const col = l.ssp ? SSP_COLOR[l.ssp] : isFocus(l) ? focusCol : grayCol;
      lg.append("path").attr("class", "link main").attr("d", path(l)).attr("stroke", col)
        .attr("stroke-width", Math.max(1, l.width)).attr("opacity", l.ssp ? (isDark() ? 0.8 : 0.6) : isFocus(l) ? 0.9 : 0.75).datum(l);
    });

    const ng = svg.append("g");
    g.nodes.forEach((n) => {
      const gn = ng.append("g");
      const h = n.y1 - n.y0;
      const cy = (n.y0 + n.y1) / 2;
      gn.append("rect").attr("x", n.x0).attr("y", n.y0).attr("width", n.x1 - n.x0).attr("height", Math.max(1, h)).attr("fill", n.depth === 0 ? SSP_COLOR[n.ssp] : nodeCol);
      if (h >= 12 || n.depth === 2) {
        const bold = n.depth === 2 && FOCUS.includes(n.id.slice(2));
        const two = h >= 26;
        const left = n.depth === 0;
        const x = left ? n.x0 - 8 : n.x1 + 8;
        const anchor = left ? "end" : "start";
        gn.append("text").attr("x", x).attr("text-anchor", anchor).attr("y", two ? cy - 2 : cy + 4).attr("font-weight", bold ? 700 : 400)
          .text(two ? n.label : `${n.label}  ${fmt.format(n.value)}`);
        if (two) gn.append("text").attr("class", "sub").attr("x", x).attr("text-anchor", anchor).attr("y", cy + 12).text(fmt.format(n.value));
      }
    });

    const tip = $("tip");
    const mains = lg.selectAll(".link.main");
    mains.attr("pointer-events", "stroke")
      .on("pointermove", (ev, l) => {
        const r = chart.getBoundingClientRect();
        tip.hidden = false;
        tip.textContent = `${l.source.label} → ${l.target.label}: ${fmt.format(l.value)} Seller-Einträge (${pct(l.value / total)})`;
        tip.style.left = Math.max(4, Math.min(ev.clientX - r.left + 12, W - tip.offsetWidth - 4)) + "px";
        tip.style.top = ev.clientY - r.top + 14 + "px";
        mains.classed("dim", (d) => d !== l);
      })
      .on("pointerleave", () => { tip.hidden = true; mains.classed("dim", false); });

    startParticles(ctx, W, H, g.links, mains.nodes(), total);
  }

  function startParticles(ctx, W, H, links, paths, total) {
    const budget = Math.min(900, Math.max(250, Math.round(W * 1.0)));
    const ps = [];
    links.forEach((l, i) => {
      const el = paths[i];
      const len = el.getTotalLength();
      const N = 60;
      const pts = [];
      for (let k = 0; k <= N; k++) { const p = el.getPointAtLength((len * k) / N); pts.push([p.x, p.y]); }
      const count = Math.max(2, Math.round((l.value / total) * budget));
      const isFocus = !l.ssp && FOCUS.includes(l.tld);
      const tone = isDark() ? d3.color(SSP_COLOR[l.ssp] || "#888").brighter(0.7).formatHex() : d3.color(SSP_COLOR[l.ssp] || "#888").darker(0.9).formatHex();
      const colors = l.ssp ? [tone, "#ffffff"] : isFocus ? [cssVar("--flow-dot-focus")] : [cssVar("--flow-dot-a"), cssVar("--flow-dot-b")];
      for (let k = 0; k < count; k++) {
        ps.push({
          pts, t: Math.random(), v: 0.00004 + Math.random() * 0.00008,
          o: (Math.random() - 0.5) * l.width * 0.9,
          c: colors[(Math.random() * colors.length) | 0], r: 0.7 + Math.random() * 1.1,
        });
      }
    });
    const draw = (dt) => {
      ctx.clearRect(0, 0, W, H);
      ctx.globalCompositeOperation = "source-over";
      for (const p of ps) {
        if (dt) { p.t += p.v * dt; if (p.t > 1) p.t -= 1; }
        const f = p.t * (p.pts.length - 1);
        const i = Math.min(f | 0, p.pts.length - 2), a = p.pts[i], b = p.pts[i + 1], u = f - i;
        ctx.globalAlpha = Math.sin(p.t * Math.PI) * 0.7;
        ctx.fillStyle = p.c;
        ctx.beginPath();
        ctx.arc(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u + p.o, p.r, 0, 6.283);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    };
    if (reduceMotion.matches) { draw(0); return; }
    let last = performance.now();
    // Zeitgeber statt requestAnimationFrame: läuft auch in eingebetteten Fenstern, die Bildaufrufe drosseln
    anim = setInterval(() => { const now = performance.now(); draw(Math.min(now - last, 80)); last = now; }, 33);
  }

  /* ---------- Weitere Bereiche ---------- */
  function sspName(id) { return state.data.ssps.find((s) => s.id === id).name; }

  // Rollenverhältnis: Seller-Einträge je SSP nach Typ. Intermediary mit Domain google.com gilt als Google-Bidding-Weg.
  function renderRoles() {
    const d = state.data;
    const cat = [
      ["PUBLISHER", "Publisher", "var(--role-pub)"],
      ["BOTH", "Beides", "var(--role-both)"],
      ["NICHT_ANGEGEBEN", "Typ nicht angegeben", "var(--role-nd)"],
      ["INT_OTHER", "Intermediary, andere", "var(--role-int)"],
      ["INT_GOOGLE", "Intermediary über google.com", "var(--role-google)"],
    ];
    const rows = d.ssps.map((s) => {
      const c = {};
      d.cube.filter((r) => r.ssp === s.id).forEach((r) => {
        const k = r.type === "INTERMEDIARY" ? (r.g ? "INT_GOOGLE" : "INT_OTHER") : r.type;
        c[k] = (c[k] || 0) + r.n;
      });
      const n = d3.sum(Object.values(c));
      const segs = cat.filter(([k]) => c[k]).map(([k, l, col]) => `<span class="seg" style="width:${(c[k] / n) * 100}%;background:${col}" title="${l}: ${fmt.format(c[k])} Einträge (${pct(c[k] / n)})"></span>`).join("");
      const inter = ((c.INT_OTHER || 0) + (c.INT_GOOGLE || 0)) / n;
      return `<div class="orow roles"><span class="oname"><i style="background:${SSP_COLOR[s.id]}"></i>${s.name}</span><div class="stack">${segs}</div><span class="onum">${pct(inter)}</span><span class="onum dim">${fmt.format(n)}</span></div>`;
    }).join("");
    $("roles").innerHTML = `<h2 id="ro-h">Rollenverhältnis je SSP</h2>
      <p>Anteil der Seller-Einträge nach Rolle. Ein Eintrag mit der Domain google.com und dem Typ Intermediary gilt als Weg über Google-Bidding (Exchange Bidding, Open Bidding). Die Dateien sagen dazu nicht mehr.</p>
      <div class="legend">${cat.filter(([k]) => k !== "NICHT_ANGEGEBEN").map(([, l, c]) => `<span><i style="background:${c}"></i>${l}</span>`).join("")}</div>
      <div class="orow roles rhead"><span></span><span></span><span class="onum">Intermediary gesamt</span><span class="onum">Einträge</span></div>
      ${rows}`;
  }

  const shortOf = (x) => x.short || x.name.slice(0, 2).toUpperCase();

  function renderOverlap() {
    const d = state.data, o = d.analysis.direct;
    const multi = o.domains - o.by_count["1"];
    const seg = (v, n, c, l) => `<span class="seg" style="width:${(v / n) * 100}%;background:${c}" title="${l}: ${fmt.format(v)} Domains (${pct(v / n)})"></span>`;
    const rows = d.ssps.map((s) => {
      const p = o.per_ssp[s.id];
      return `<div class="orow"><span class="oname"><i style="background:${SSP_COLOR[s.id]}"></i>${s.name}</span>
        <div class="stack">${seg(p.exclusive, p.n, "var(--band-1)", "nur bei dieser SSP")}${seg(p.few, p.n, "var(--band-2)", "bei 2 bis 3 SSPs")}${seg(p.many, p.n, "var(--band-3)", "bei 4 oder mehr SSPs")}</div>
        <span class="onum">${pct(p.exclusive / p.n)}</span></div>`;
    }).join("");
    $("ov-a").innerHTML = `<h2 id="ova-h">Überschneidung direkter Publisher</h2>
      <div class="hero"><b>${pct(multi / o.domains)}</b><span>der ${fmt.format(o.domains)} direkt gelisteten Publisher-Domains sind bei mehr als einer SSP direkt gelistet (${fmt.format(multi)}).</span></div>
      <p>Direkt gelistete Domains je SSP, nach Zahl der SSPs, bei denen sie direkt stehen. Rechts der Anteil, der nur bei dieser SSP direkt gelistet ist.</p>
      <div class="legend"><span><i style="background:var(--band-1)"></i>nur bei dieser SSP</span><span><i style="background:var(--band-2)"></i>bei 2 bis 3 SSPs</span><span><i style="background:var(--band-3)"></i>bei 4 oder mehr</span></div>
      ${rows}`;

    const max = Math.max(...o.combos.map((c) => c.n));
    const head = d.ssps.map((s) => `<span title="${s.name}">${shortOf(s)}</span>`).join("");
    const crows = o.combos.map((c) => `<div class="crow"><div class="cdots">${d.ssps.map((s) => `<b class="${c.ssps.includes(s.id) ? "on" : ""}" style="${c.ssps.includes(s.id) ? `background:${SSP_COLOR[s.id]};border-color:${SSP_COLOR[s.id]}` : ""}" title="${s.name}"></b>`).join("")}</div>
      <div class="ctrack"><div class="cfill" style="width:${(c.n / max) * 100}%"></div></div><span class="onum">${fmt.format(c.n)}</span></div>`).join("");
    $("ov-b").innerHTML = `<h2 id="ovb-h">Häufigste SSP-Kombinationen</h2>
      <p>Die ${["", "eine", "zwei", "drei", "vier", "fünf", "sechs"][o.combos.length] || o.combos.length} häufigsten Kombinationen von SSPs, bei denen dieselbe Domain direkt gelistet ist. Gezählt wird je genau diese Kombination.</p>
      <div class="crow chead"><div class="cdots">${head}</div><span></span><span></span></div>
      ${crows}
      <p class="note" style="margin-top:12px">${d.ssps.map((s) => `${shortOf(s)} ${s.name}`).join(", ")}</p>`;
  }

  // Sonderauswertung .de: Rollenmix je SSP und Mehrfachlistung der direkt gelisteten Publisher.
  function renderDe() {
    const d = state.data, de = d.analysis.de, o = d.analysis.direct;
    const deRows = d.cube.filter((r) => r.tld === de.tld);
    const entries = d3.sum(deRows, (r) => r.n);
    $("de-intro").textContent = `${fmt.format(de.domains)} eindeutige .de-Domains mit ${fmt.format(entries)} Einträgen, ${pct(entries / d3.sum(d.cube, (r) => r.n))} aller Einträge. Die Basis ist klein: Einzelne Domains verschieben die Prozentwerte deutlich.`;

    const cat = [["PUBLISHER", "Publisher", "var(--role-pub)"], ["BOTH", "Beides", "var(--role-both)"], ["NICHT_ANGEGEBEN", "Typ nicht angegeben", "var(--role-nd)"], ["INTERMEDIARY", "Intermediary", "var(--role-int)"]];
    const bar = (c, n) => cat.filter(([k]) => c[k]).map(([k, l, col]) => `<span class="seg" style="width:${(c[k] / n) * 100}%;background:${col}" title="${l}: ${fmt.format(c[k])} Einträge (${pct(c[k] / n)})"></span>`).join("");
    const count = (rows) => { const c = {}; rows.forEach((r) => { c[r.type] = (c[r.type] || 0) + r.n; }); return c; };
    const line = (name, dot, rows) => {
      const c = count(rows), n = d3.sum(Object.values(c));
      return `<div class="orow roles"><span class="oname">${dot ? `<i style="background:${dot}"></i>` : ""}${name}</span><div class="stack">${bar(c, n)}</div><span class="onum">${pct((c.INTERMEDIARY || 0) / n)}</span><span class="onum dim">${fmt.format(n)}</span></div>`;
    };
    const ref = d.cube.filter((r) => !(r.type === "INTERMEDIARY" && r.g));
    $("de-a").innerHTML = `<h3 id="dea-h">Rollen bei .de-Domains</h3>
      <p>Anteil der .de-Einträge je SSP nach Rolle. Zum Vergleich steht unten der gesamte Datensatz ohne die Wege über google.com.</p>
      <div class="legend">${cat.filter(([k]) => k !== "NICHT_ANGEGEBEN").map(([, l, c]) => `<span><i style="background:${c}"></i>${l}</span>`).join("")}</div>
      <div class="orow roles rhead"><span></span><span></span><span class="onum">Interm.</span><span class="onum">Einträge</span></div>
      ${d.ssps.map((s) => line(s.name, SSP_COLOR[s.id], deRows.filter((r) => r.ssp === s.id))).join("")}
      <div class="sep"></div>
      ${line("Alle Einträge", null, ref)}`;

    const od = de.direct;
    const dist = (by, n) => { const v = (k) => by[String(k)] || 0; const ks = Object.keys(by).map(Number); const few = ks.filter((k) => k >= 2 && k <= 3).reduce((a, k) => a + v(k), 0); const many = ks.filter((k) => k >= 4).reduce((a, k) => a + v(k), 0); return { one: v(1), few, many, n }; };
    const rowB = (name, x) => `<div class="orow"><span class="oname">${name}</span><div class="stack">
      <span class="seg" style="width:${(x.one / x.n) * 100}%;background:var(--band-1)" title="nur bei dieser SSP: ${fmt.format(x.one)} Domains (${pct(x.one / x.n)})"></span>
      <span class="seg" style="width:${(x.few / x.n) * 100}%;background:var(--band-2)" title="bei 2 bis 3 SSPs: ${fmt.format(x.few)} Domains (${pct(x.few / x.n)})"></span>
      <span class="seg" style="width:${(x.many / x.n) * 100}%;background:var(--band-3)" title="bei 4 oder mehr SSPs: ${fmt.format(x.many)} Domains (${pct(x.many / x.n)})"></span></div>
      <span class="onum">${pct(1 - x.one / x.n)}</span></div>`;
    const xd = dist(od.by_count, od.domains), xa = dist(o.by_count, o.domains);
    $("de-b").innerHTML = `<h3 id="deb-h">Mehrfachlistung bei .de-Publishern</h3>
      <div class="hero"><b>${pct(1 - xd.one / xd.n)}</b><span>der ${fmt.format(od.domains)} direkt gelisteten .de-Publisher-Domains sind bei mehr als einer SSP direkt gelistet. Im gesamten Datensatz sind es ${pct(1 - xa.one / xa.n)}.</span></div>
      <p>Domains nach Zahl der SSPs, bei denen sie direkt gelistet sind. Rechts der Anteil mit mehr als einer SSP.</p>
      <div class="legend"><span><i style="background:var(--band-1)"></i>bei einer SSP</span><span><i style="background:var(--band-2)"></i>bei 2 bis 3 SSPs</span><span><i style="background:var(--band-3)"></i>bei 4 oder mehr</span></div>
      <div class="orow rhead"><span></span><span></span><span class="onum">mehrfach</span></div>
      ${rowB(".de", xd)}${rowB("Alle Domains", xa)}`;
  }

  // Nur sichtbar, wenn ein Vormonat vorliegt.
  function renderChanges() {
    const d = state.data;
    const box = $("changes");
    box.hidden = !d.changes;
    if (!d.changes) return;
    const rows = d.ssps.map((s) => {
      const c = d.changes[s.id];
      return c ? `<tr><td>${s.name}</td><td>${fmt.format(s.sellers)}</td><td>+${fmt.format(c.neu)}</td><td>-${fmt.format(c.entfernt)}</td></tr>` : "";
    }).join("");
    box.innerHTML = `<h2 id="ch-h">Veränderung zum Vormonat</h2><p>Neue und entfernte Seller-IDs je Datei.</p><div class="tscroll"><table><thead><tr><th>SSP</th><th>Seller</th><th>neu</th><th>entfernt</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  // Datenqualität über alle Dateien zusammen, ohne Aufschlüsselung je SSP.
  function renderQuality() {
    const d = state.data;
    const q = Object.values(d.quality);
    const sum = (f) => d3.sum(q, f);
    const total = sum((x) => x.sellers);
    const stat = (v, l) => `<div><b>${fmt.format(v)}</b><span>${l}</span></div>`;
    $("quality").innerHTML = `<h2 id="q-h">Datenqualität</h2>
      <p>Die Dateien wurden formal bereinigt (Leerzeichen, Schema, Pfad, Schreibweise, www). Dabei wurde kein Eintrag entfernt, die Originalwerte bleiben im Snapshot erhalten.</p>
      <div class="hero"><b>${pct(sum((x) => x.korrigiert) / total)}</b><span>der ${fmt.format(total)} Einträge brauchten eine solche Korrektur an der Domain.</span></div>
      <div class="kv">
        ${stat(sum((x) => x.flags.domain_fehlt || 0), "Einträge ohne Domain")}
        ${stat(sum((x) => x.flags.name_fehlt || 0), "Einträge ohne Namen")}
        ${stat(sum((x) => x.flags.domain_ungueltig || 0), "Einträge mit ungültiger Domain")}
        ${stat(sum((x) => x.flags.id_doppelt || 0), "Einträge mit doppelter Seller-ID")}
      </div>
      <p class="note">Bei Einträgen, die als confidential gekennzeichnet sind, fehlen Name und Domain absichtlich. Sie zählen hier nicht als fehlend.</p>`;
  }

  function renderMethod() {
    const d = state.data;
    const items = d.ssps.map((s) =>
      `<dt>${s.name}</dt><dd><a href="${s.url}" rel="noopener">${s.url}</a><br><span class="note">abgerufen ${s.fetched_at ? new Date(s.fetched_at).toLocaleString("de-DE") : "-"}${s.bytes ? ", " + fmt.format(s.bytes) + " Bytes" : ""}</span><br><code>SHA-256 ${s.sha256 || "-"}</code></dd>`
    ).join("");
    $("method").className = "panel meth";
    $("method").innerHTML = `<details><summary><h2 id="m-h">Methodik und Quellen</h2></summary>
      <p>Ausgewertet werden die öffentlichen sellers.json-Dateien von sechs SSPs. Die Auswahl ist nicht vollständig und folgt keiner Rangfolge. Die Dateien werden abgerufen, Weiterleitungen werden verfolgt. Aus jedem Eintrag werden Seller-ID, Name, Domain, Typ und, falls vorhanden, is_confidential übernommen. Die Domain wird bereinigt (Leerzeichen, Schema, Pfad, Port, Endpunkt, Kleinschreibung, führendes www; bei mehreren Domains die erste). Die Länderendung ist der letzte Teil der bereinigten Domain.</p>
      <p>Gezählt werden Seller-Einträge. „Direkt gelistet“ bedeutet: mindestens ein Eintrag der Domain hat den Typ Publisher. Ein Eintrag mit Typ Intermediary und der Domain google.com gilt als Weg über Google-Bidding. Die Dateien geben dazu nicht mehr her. Die Zahlen beschreiben den Inhalt der Dateien zum Abrufzeitpunkt, nicht Umsatz oder Impressions.</p>
      <dl>${items}</dl></details>`;
  }
})();
