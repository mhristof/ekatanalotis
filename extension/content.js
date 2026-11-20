// On a store's product page, shows the product's price history in every
// store that sells it, in a panel at the bottom right.

(() => {
  // in a fixed order, so a store keeps its color on every product
  const STORES = {
    kritikos: { name: "Kritikos", light: "#2a78d6", dark: "#3987e5" },
    ab: { name: "AB", light: "#eb6834", dark: "#d95926" },
    mymarket: { name: "My Market", light: "#1baf7a", dark: "#199e70" },
    sklavenitis: { name: "Sklavenitis", light: "#eda100", dark: "#c98500" },
    xalkiadakis: { name: "Xalkiadakis", light: "#e87ba4", dark: "#d55181" },
    marketin: { name: "Market In", light: "#008300", dark: "#008300" },
    efresh: { name: "e-Fresh", light: "#6250d6", dark: "#9085e9" },
  };
  const RANGES = [
    ["3M", 91],
    ["1Y", 365],
    ["All", null],
  ];
  const DAY = 24 * 60 * 60 * 1000;
  const SVG = "http://www.w3.org/2000/svg";

  // the store and its product code of the page, or null
  function detect() {
    const host = location.hostname;

    if (host.endsWith("sklavenitis.gr")) {
      const tile = document.querySelector(".product-detail[data-plugin-product]");

      try {
        const sku = tile && JSON.parse(tile.getAttribute("data-plugin-product")).sku;

        return sku ? { store: "sklavenitis", code: String(sku) } : null;
      } catch {
        return null;
      }
    }

    if (host.endsWith("ab.gr")) {
      const m = location.pathname.match(/\/p\/(\d+)\/?$/);

      return m ? { store: "ab", code: m[1] } : null;
    }

    return null;
  }

  function lookup(store, code) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type: "lookup", store, code }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else if (response.error) {
          reject(new Error(response.error));
        } else {
          resolve(response.result);
        }
      });
    });
  }

  const day = (iso) => Date.parse(iso + "T00:00:00Z");
  const iso = (t) => new Date(t).toISOString().slice(0, 10);
  const euro = (p) => (p == null ? "–" : p.toFixed(2).replace(".", ",") + " €");

  function el(tag, attrs = {}, ...children) {
    const e = tag.startsWith("svg:")
      ? document.createElementNS(SVG, tag.slice(4))
      : document.createElement(tag);

    for (const [k, v] of Object.entries(attrs)) {
      e.setAttribute(k, v);
    }

    for (const c of children) {
      e.append(c);
    }

    return e;
  }

  // [{store, points: [[time, price], ...], end}] with the latest price as
  // the last point, ending at its date (or the last change when the store
  // didn't list it in its latest prices)
  function series(result) {
    const out = [];

    for (const store of Object.keys(STORES)) {
      const s = result.stores[store];

      if (!s) {
        continue;
      }

      const points = s.history.map(([d, p]) => [day(d), p]);

      if (s.price != null && (!points.length || points[points.length - 1][1] !== s.price)) {
        points.push([day(s.date), s.price]);
      }

      if (points.length) {
        const end = s.date ? Math.max(day(s.date), points[points.length - 1][0]) : points[points.length - 1][0];
        out.push({ store, points, end });
      }
    }

    return out;
  }

  // the price at time t, or null outside the series
  function priceAt(s, t) {
    if (t < s.points[0][0] || t > s.end) {
      return null;
    }

    let price = null;

    for (const [time, p] of s.points) {
      if (time > t) {
        break;
      }

      price = p;
    }

    return price;
  }

  function ticks(min, max, count) {
    const step0 = (max - min) / count;
    const mag = 10 ** Math.floor(Math.log10(step0));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0);
    const out = [];

    for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) {
      out.push(Math.round(v * 100) / 100);
    }

    return out;
  }

  const STYLE = `
    :host { all: initial; }
    .panel {
      --surface: #fcfcfb; --text: #0b0b0b; --text-2: #52514e; --muted: #8a8984;
      --grid: #e6e5e1; --border: #d9d8d3; --accent: #2a78d6;
      color-scheme: light;
      position: fixed; right: 16px; bottom: 16px; z-index: 2147483647;
      width: 420px; max-width: calc(100vw - 32px); box-sizing: border-box;
      background: var(--surface); color: var(--text);
      border: 1px solid var(--border); border-radius: 10px;
      box-shadow: 0 6px 24px rgba(0,0,0,.18);
      font: 13px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif;
    }
    @media (prefers-color-scheme: dark) {
      .panel {
        --surface: #1a1a19; --text: #f0efec; --text-2: #c3c2b7; --muted: #8f8e86;
        --grid: #2e2e2c; --border: #3a3a37; --accent: #3987e5;
        color-scheme: dark;
      }
    }
    header { display: flex; align-items: center; gap: 8px; padding: 10px 12px; cursor: pointer; }
    header .title { flex: 1; min-width: 0; }
    header .name { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    header .sub { color: var(--text-2); font-size: 12px; }
    header button { all: unset; cursor: pointer; color: var(--text-2); padding: 2px 6px; font-size: 16px; }
    .body { padding: 0 12px 12px; }
    .collapsed .body { display: none; }
    .ranges { display: flex; gap: 4px; margin-bottom: 6px; }
    .ranges button {
      all: unset; cursor: pointer; padding: 2px 8px; border-radius: 6px;
      color: var(--text-2); border: 1px solid var(--border); font-size: 12px;
    }
    .ranges button[aria-pressed="true"] { color: var(--text); border-color: var(--text-2); font-weight: 600; }
    .chart { position: relative; }
    svg { display: block; width: 100%; height: auto; overflow: visible; }
    .axis { fill: var(--muted); font-size: 10px; }
    .tip {
      position: absolute; pointer-events: none; display: none;
      background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
      padding: 6px 8px; box-shadow: 0 2px 8px rgba(0,0,0,.15); font-size: 12px; white-space: nowrap;
    }
    .tip .date { color: var(--text-2); margin-bottom: 2px; }
    .tip .row { display: flex; align-items: center; gap: 6px; }
    .tip b { min-width: 52px; text-align: right; }
    .tip span { color: var(--text-2); }
    .key { display: inline-block; width: 12px; height: 0; border-top: 2px solid; vertical-align: middle; }
    .legend { display: flex; flex-wrap: wrap; gap: 4px 12px; margin: 6px 0 8px; color: var(--text-2); font-size: 12px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th { text-align: left; color: var(--muted); font-weight: 500; padding: 2px 4px; border-bottom: 1px solid var(--grid); }
    td { padding: 3px 4px; border-bottom: 1px solid var(--grid); }
    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
    tr.here td { font-weight: 600; }
    .cheapest { color: var(--accent); font-weight: 600; }
    .note { color: var(--muted); font-size: 11px; margin-top: 6px; }
    .message { color: var(--text-2); padding: 0 12px 12px; }
  `;

  let host = null;
  let state = { collapsed: false, range: 365 };

  try {
    Object.assign(state, JSON.parse(localStorage.getItem("ekatanalotis") || "{}"));
  } catch {
    // keep the defaults
  }

  function save() {
    try {
      localStorage.setItem("ekatanalotis", JSON.stringify({ collapsed: state.collapsed, range: state.range }));
    } catch {
      // not remembered
    }
  }

  function dark() {
    return matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function color(store) {
    return STORES[store][dark() ? "dark" : "light"];
  }

  function chart(all, here) {
    const W = 396;
    const H = 180;
    const left = 40;
    const right = 8;
    const top = 8;
    const bottom = 20;
    const last = Math.max(...all.map((s) => s.end));
    const first = Math.min(...all.map((s) => s.points[0][0]));
    const from = state.range ? Math.max(first, last - state.range * DAY) : first;
    const to = Math.max(last, from + DAY);
    const visible = all
      .map((s) => ({ ...s, shown: s.points.filter(([t]) => t >= from).map(([, p]) => p).concat(priceAt(s, from) ?? []) }))
      .filter((s) => s.end >= from && s.shown.length);
    const values = visible.flatMap((s) => s.shown);
    let lo = Math.min(...values);
    let hi = Math.max(...values);
    const pad = Math.max((hi - lo) * 0.08, 0.05);
    lo = Math.max(0, lo - pad);
    hi += pad;
    const x = (t) => left + ((t - from) / (to - from)) * (W - left - right);
    const y = (p) => top + (1 - (p - lo) / (hi - lo)) * (H - top - bottom);
    const svg = el("svg:svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Price history per store" });

    for (const v of ticks(lo, hi, 4)) {
      svg.append(el("svg:line", { x1: left, x2: W - right, y1: y(v), y2: y(v), stroke: "var(--grid)" }));
      svg.append(el("svg:text", { x: left - 6, y: y(v) + 3, "text-anchor": "end", class: "axis" }, euro(v)));
    }

    for (const t of [from, (from + to) / 2, to]) {
      const anchor = t === from ? "start" : t === to ? "end" : "middle";
      svg.append(el("svg:text", { x: x(t), y: H - 4, "text-anchor": anchor, class: "axis" }, iso(t)));
    }

    // the page's store last, on top
    const order = visible.slice().sort((a, b) => (a.store === here) - (b.store === here));

    for (const s of order) {
      let d = "";
      const start = priceAt(s, from);
      let started = false;

      if (start != null) {
        d = `M${x(from)},${y(start)}`;
        started = true;
      }

      for (const [t, p] of s.points) {
        if (t < from) {
          continue;
        }

        d += started ? `H${x(t)}V${y(p)}` : `M${x(t)},${y(p)}`;
        started = true;
      }

      d += `H${x(s.end)}`;
      svg.append(
        el("svg:path", {
          d,
          fill: "none",
          stroke: color(s.store),
          "stroke-width": s.store === here ? 3 : 2,
          "stroke-linejoin": "round",
          "stroke-linecap": "round",
        }),
      );
    }

    const hair = el("svg:line", { y1: top, y2: H - bottom, stroke: "var(--text-2)", "stroke-width": 1, visibility: "hidden" });
    const dots = el("svg:g");
    const hit = el("svg:rect", { x: left, y: 0, width: W - left - right, height: H, fill: "transparent" });
    svg.append(hair, dots, hit);

    const tip = el("div", { class: "tip" });
    const box = el("div", { class: "chart" }, svg, tip);

    function show(event) {
      const r = svg.getBoundingClientRect();
      const px = ((event.clientX - r.left) / r.width) * W;
      const t = Math.round((from + ((px - left) / (W - left - right)) * (to - from)) / DAY) * DAY;
      const at = Math.min(Math.max(t, from), to);
      hair.setAttribute("x1", x(at));
      hair.setAttribute("x2", x(at));
      hair.setAttribute("visibility", "visible");
      dots.replaceChildren();
      tip.replaceChildren(el("div", { class: "date" }, iso(at)));
      const rows = visible
        .map((s) => [s, priceAt(s, at)])
        .filter(([, p]) => p != null)
        .sort((a, b) => a[1] - b[1]);

      for (const [s, p] of rows) {
        dots.append(
          el("svg:circle", { cx: x(at), cy: y(p), r: 4, fill: color(s.store), stroke: "var(--surface)", "stroke-width": 2 }),
        );
        const key = el("i", { class: "key" });
        key.style.borderColor = color(s.store);
        tip.append(el("div", { class: "row" }, key, el("b", {}, euro(p)), el("span", {}, STORES[s.store].name)));
      }

      tip.style.display = rows.length ? "block" : "none";
      const bx = ((x(at) / W) * r.width);
      tip.style.left = `${bx > r.width / 2 ? bx - tip.offsetWidth - 10 : bx + 10}px`;
      tip.style.top = "4px";
    }

    function hide() {
      hair.setAttribute("visibility", "hidden");
      dots.replaceChildren();
      tip.style.display = "none";
    }

    hit.addEventListener("pointermove", show);
    hit.addEventListener("pointerleave", hide);

    return box;
  }

  function table(result, here) {
    const rows = Object.keys(STORES)
      .filter((s) => result.stores[s])
      .map((s) => [s, result.stores[s]])
      .sort((a, b) => (a[1].price ?? Infinity) - (b[1].price ?? Infinity));
    const cheapest = rows[0]?.[1].price;
    const herePrice = result.stores[here]?.price;
    const body = el("tbody");

    for (const [store, s] of rows) {
      const key = el("i", { class: "key" });
      key.style.borderColor = color(store);
      const diff =
        s.price != null && herePrice != null && store !== here
          ? `${s.price > herePrice ? "+" : ""}${Math.round(((s.price - herePrice) / herePrice) * 100)}%`
          : "";
      const price = el("td", { class: "num" + (s.price != null && s.price === cheapest ? " cheapest" : "") }, euro(s.price));
      const unit = s.unitPrice != null ? `${euro(s.unitPrice)}/${s.unit}` : "";
      body.append(
        el(
          "tr",
          { class: store === here ? "here" : "" },
          el("td", {}, key, " ", STORES[store].name),
          price,
          el("td", { class: "num" }, diff),
          el("td", { class: "num" }, unit),
          el("td", { class: "num" }, s.date || "not listed"),
        ),
      );
    }

    return el(
      "table",
      {},
      el(
        "thead",
        {},
        el(
          "tr",
          {},
          el("th", {}, "Store"),
          el("th", { class: "num" }, "Price"),
          el("th", { class: "num" }, "vs here"),
          el("th", { class: "num" }, "Unit"),
          el("th", { class: "num" }, "Date"),
        ),
      ),
      body,
    );
  }

  function panel() {
    if (!host || !host.isConnected) {
      host = el("div", { id: "ekatanalotis" });
      host.attachShadow({ mode: "open" });
      document.documentElement.append(host);
    }

    const root = host.shadowRoot;
    root.replaceChildren(el("style", {}, STYLE));
    const p = el("div", { class: "panel" + (state.collapsed ? " collapsed" : "") });
    root.append(p);

    return p;
  }

  function header(p, name, sub) {
    const toggle = el("button", { "aria-label": "Collapse" }, state.collapsed ? "▴" : "▾");
    const h = el("header", {}, el("div", { class: "title" }, el("div", { class: "name" }, name), el("div", { class: "sub" }, sub)), toggle);
    h.addEventListener("click", () => {
      state.collapsed = !state.collapsed;
      save();
      p.classList.toggle("collapsed", state.collapsed);
      toggle.textContent = state.collapsed ? "▴" : "▾";
    });
    p.append(h);
  }

  function render(result, here) {
    const p = panel();
    const all = series(result);
    const listed = Object.values(result.stores).filter((s) => s.price != null).length;
    const name = [result.product.name, result.product.size].filter(Boolean).join(" · ");
    header(p, name, `${listed} of ${Object.keys(result.stores).length} stores list it`);
    const body = el("div", { class: "body" });
    p.append(body);

    const ranges = el("div", { class: "ranges" });
    const holder = el("div");

    function draw() {
      holder.replaceChildren(all.length ? chart(all, here) : el("div", { class: "note" }, "No price history yet"));
    }

    for (const [label, days] of RANGES) {
      const b = el("button", { "aria-pressed": String(state.range === days) }, label);
      b.addEventListener("click", () => {
        state.range = days;
        save();
        ranges.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
        draw();
      });
      ranges.append(b);
    }

    const legend = el("div", { class: "legend" });

    for (const s of all) {
      const key = el("i", { class: "key" });
      key.style.borderColor = color(s.store);
      legend.append(el("span", {}, key, " ", STORES[s.store].name));
    }

    draw();
    body.append(
      ranges,
      holder,
      legend,
      table(result, here),
      el("div", { class: "note" }, "Matched by barcode or name; check the size before you switch."),
    );
  }

  function message(text) {
    const p = panel();
    header(p, "ekatanalotis", "");
    p.append(el("div", { class: "message body" }, text));
  }

  let current = null;

  async function check() {
    const found = detect();
    const key = found ? `${found.store}:${found.code}` : null;

    if (key === current) {
      return;
    }

    current = key;

    if (!found) {
      host?.remove();
      host = null;
      return;
    }

    try {
      const result = await lookup(found.store, found.code);

      if (current !== key) {
        return;
      }

      if (result) {
        render(result, found.store);
      } else {
        host?.remove();
        host = null;
      }
    } catch (error) {
      if (current === key) {
        message(`Could not load prices: ${error.message}`);
      }
    }
  }

  check();
  // the stores are single page apps: follow navigation
  setInterval(check, 1000);
})();
