// On a store's product page, shows the product's price history in every
// store that sells it, in a panel at the bottom right, in Greek or English:
// the latest prices, and the price history graph when the user opens it.

(() => {
  // in a fixed order, so a store keeps its color and its place in the table,
  // tooltip and legend on every product
  const STORES = {
    kritikos: { name: "Kritikos", light: "#2a78d6", dark: "#3987e5" },
    ab: { name: "AB", light: "#eb6834", dark: "#d95926" },
    mymarket: { name: "My Market", light: "#1baf7a", dark: "#199e70" },
    sklavenitis: { name: "Sklavenitis", light: "#eda100", dark: "#c98500" },
    xalkiadakis: { name: "Xalkiadakis", light: "#e87ba4", dark: "#d55181" },
    marketin: { name: "Market In", light: "#008300", dark: "#008300" },
    efresh: { name: "e-Fresh", light: "#6250d6", dark: "#9085e9" },
    masoutis: { name: "Masoutis", light: "#e34948", dark: "#e66767" },
    // the palette has 8 hues: the 9th store reuses the green of the store it
    // shares the fewest products with, told apart by a dashed line
    galaxias: { name: "Galaxias", light: "#008300", dark: "#008300", dash: true },
  };
  // [label key, days]
  const RANGES = [
    ["months3", 91],
    ["year", 365],
    ["all", null],
  ];
  // the panel's text; Greek unless the user picks English
  const TEXT = {
    el: {
      stores: {
        kritikos: "Κρητικός",
        ab: "ΑΒ",
        mymarket: "My Market",
        sklavenitis: "Σκλαβενίτης",
        xalkiadakis: "Χαλκιαδάκης",
        marketin: "Market In",
        efresh: "e-Fresh",
        masoutis: "Μασούτης",
        galaxias: "Γαλαξίας",
      },
      units: { kg: "κιλό", l: "λίτρο", piece: "τεμ.", wash: "πλύση", m: "μέτρο" },
      months3: "3Μ",
      year: "1Ε",
      all: "Όλα",
      chart: "Ιστορικό τιμών ανά κατάστημα",
      store: "Κατάστημα",
      price: "Τιμή",
      vsHere: "Διαφορά",
      unit: "Ανά μονάδα",
      date: "Ημερομηνία",
      notListed: "δεν υπάρχει",
      ago: (days) => (days <= 0 ? "σήμερα" : days === 1 ? "χθες" : `πριν από ${days} ημέρες`),
      collapse: "Σύμπτυξη",
      language: "Switch to English",
      cheaperHere: (unit) => `Φθηνότερο ανά ${unit} εδώ`,
      thePack: (price) => `${price} η συσκευασία`,
      multipack: "πολυσυσκευασία",
      singlePack: "μονή συσκευασία",
      thisOne: (unitPrice) =>
        `Αυτό: ${unitPrice}. Οι τιμές μονάδας βγαίνουν από το μέγεθος της συσκευασίας· οι προσφορές τις αλλάζουν.`,
      cheaperPack: "Φθηνότερη συσκευασία σε αυτό το κατάστημα",
      listed: (n, total) => `Σε ${n} από ${total} καταστήματα`,
      noHistory: "Δεν υπάρχει ιστορικό τιμών ακόμα",
      showHistory: "Εμφάνιση ιστορικού τιμών ▴",
      hideHistory: "Απόκρυψη ιστορικού τιμών ▾",
      matched: "Αντιστοίχιση με barcode ή όνομα· ελέγξτε το μέγεθος πριν αλλάξετε κατάστημα.",
      // ab.fix_unit(): the store gives a kg or l price per piece
      unitFixed: (stores) => `* Διορθώσαμε τη μονάδα: ${stores} τη δείχνει ανά τεμάχιο.`,
      error: (message) => `Δεν φορτώθηκαν οι τιμές: ${message}`,
    },
    en: {
      stores: Object.fromEntries(Object.entries(STORES).map(([s, v]) => [s, v.name])),
      units: {},
      months3: "3M",
      year: "1Y",
      all: "All",
      chart: "Price history per store",
      store: "Store",
      price: "Price",
      vsHere: "vs here",
      unit: "Unit",
      date: "Date",
      notListed: "not listed",
      ago: (days) => (days <= 0 ? "today" : days === 1 ? "yesterday" : `${days} days ago`),
      collapse: "Collapse",
      language: "Αλλαγή σε ελληνικά",
      cheaperHere: (unit) => `Cheaper per ${unit} here`,
      thePack: (price) => `${price} the pack`,
      multipack: "multipack",
      singlePack: "single pack",
      thisOne: (unitPrice) => `This one: ${unitPrice}. Unit prices from the pack sizes; offers change them.`,
      cheaperPack: "A cheaper pack size in this store",
      listed: (n, total) => `${n} of ${total} stores list it`,
      noHistory: "No price history yet",
      showHistory: "Show price history ▴",
      hideHistory: "Hide price history ▾",
      matched: "Matched by barcode or name; check the size before you switch.",
      unitFixed: (stores) => `* We corrected the unit: ${stores} shows it per piece.`,
      error: (message) => `Could not load prices: ${message}`,
    },
  };
  // a store's search page that finds a product by its code
  const SEARCH = {
    sklavenitis: (code) => `https://www.sklavenitis.gr/apotelesmata-anazitisis/?Query=${code}`,
    ab: (code) => `https://www.ab.gr/search?q=${code}`,
    // the page finds the product by the code alone, the name is not checked
    masoutis: (code) => `https://www.masoutis.gr/categories/item/x?${code}`,
    galaxias: (code) => `https://galaxias.shop/product/${code}`,
  };
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

    if (host.endsWith("masoutis.gr")) {
      // /categories/item/<name>?<code>, which the site rewrites to ?<code>=
      const m = location.search.match(/^\?(\d+)=?$/);

      return location.pathname.startsWith("/categories/item/") && m
        ? { store: "masoutis", code: m[1] }
        : null;
    }

    if (host === "galaxias.shop" || host.endsWith(".galaxias.shop")) {
      // /product/<sku>, the sku being the barcode
      const m = location.pathname.match(/^\/product\/(\d+)\/?$/);

      return m ? { store: "galaxias", code: m[1] } : null;
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
  // days since an ISO date, by the local calendar
  const daysAgo = (date) => Math.round((day(new Date().toLocaleDateString("sv")) - day(date)) / DAY);
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
      --cheap: #1a7f37; --dear: #cf222e;
      color-scheme: light;
      position: fixed; right: 16px; bottom: 16px; z-index: 2147483647;
      width: 420px; max-width: calc(100vw - 32px); box-sizing: border-box;
      max-height: calc(100vh - 32px); overflow-y: auto;
      background: var(--surface); color: var(--text);
      border: 1px solid var(--border); border-radius: 10px;
      box-shadow: 0 6px 24px rgba(0,0,0,.18);
      font: 13px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif;
    }
    @media (prefers-color-scheme: dark) {
      .panel {
        --surface: #1a1a19; --text: #f0efec; --text-2: #c3c2b7; --muted: #8f8e86;
        --grid: #2e2e2c; --border: #3a3a37; --accent: #3987e5;
        --cheap: #3fb950; --dear: #f85149;
        color-scheme: dark;
      }
    }
    header { display: flex; align-items: center; gap: 8px; padding: 10px 12px; cursor: pointer; }
    header .title { flex: 1; min-width: 0; }
    header .name { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    header .sub { color: var(--text-2); font-size: 12px; }
    header button { all: unset; cursor: pointer; color: var(--text-2); padding: 2px 6px; font-size: 16px; }
    .footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 8px; }
    button.lang {
      all: unset; cursor: pointer; color: var(--text-2); font-size: 11px; font-weight: 600;
      border: 1px solid var(--border); border-radius: 6px; padding: 1px 6px;
    }
    .body { padding: 0 12px 12px; }
    .collapsed .body { display: none; }
    .ranges { display: flex; gap: 4px; margin: 8px 0 6px; }
    .toggle {
      all: unset; cursor: pointer; display: block;
      color: var(--accent); font-size: 12px; font-weight: 600;
    }
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
    .key { display: inline-block; width: 14px; height: 0; border-top: 2px solid; vertical-align: middle; }
    .legend { display: flex; flex-wrap: wrap; gap: 4px 12px; margin: 6px 0 8px; color: var(--text-2); font-size: 12px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th { text-align: left; color: var(--muted); font-weight: 500; padding: 2px 4px; border-bottom: 1px solid var(--grid); }
    td { padding: 3px 4px; border-bottom: 1px solid var(--grid); }
    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
    th button.sort { all: unset; cursor: pointer; color: inherit; font-weight: inherit; white-space: nowrap; }
    th button.sort:hover, th button.sort.active { color: var(--text-2); }
    /* fixed width, so the label doesn't move when the arrow changes */
    th .arrow { display: inline-block; width: 1em; margin-left: 2px; text-align: center; font-size: 10px; opacity: .45; }
    th .active .arrow { opacity: 1; }
    tr.here td { font-weight: 600; }
    /* the page's store's row is bold, so these are colour only */
    .cheapest { color: var(--cheap); }
    .dearest { color: var(--dear); }
    .note { color: var(--muted); font-size: 11px; margin-top: 6px; }
    .message { color: var(--text-2); padding: 0 12px 12px; }
    .packs { border: 1px solid var(--accent); border-radius: 8px; padding: 6px 8px; margin-bottom: 10px; }
    .packs .head { font-weight: 600; margin-bottom: 2px; }
    .packs .alt { padding: 4px 0; border-top: 1px solid var(--grid); }
    .packs .head + .alt { border-top: 0; }
    .packs a, .packs .what { color: var(--text); text-decoration: none; }
    .packs a:hover { text-decoration: underline; }
    .packs .meta { display: flex; gap: 10px; align-items: baseline; }
    .packs .unit { font-variant-numeric: tabular-nums; white-space: nowrap; font-weight: 600; }
    .packs .save { color: var(--accent); font-weight: 600; white-space: nowrap; }
    .packs .price { color: var(--text-2); font-variant-numeric: tabular-nums; white-space: nowrap; }
    .packs .tag { color: var(--muted); font-size: 11px; white-space: nowrap; }
  `;

  let host = null;
  let state = { collapsed: false, range: 365 };
  // in chrome.storage, not the site's localStorage, so one choice covers
  // every store's site: the language, and whether the price history graph
  // is shown (only the latest prices by default)
  // sort: the prices table's column and direction, "-" for descending
  const settings = { lang: "el", history: false, sort: "store" };
  const SORTS = ["store", "-store", "price", "-price"];
  const VALID = {
    lang: (v) => v in TEXT,
    history: (v) => typeof v === "boolean",
    sort: (v) => SORTS.includes(v),
  };
  const t = () => TEXT[settings.lang];
  const storeName = (store) => t().stores[store];
  const unitName = (unit) => t().units[unit] || unit;
  // what the panel shows, to draw it again in the other language
  let shown = null;

  const settingsLoaded = new Promise((resolve) => {
    try {
      chrome.storage.local.get(Object.keys(settings), (items) => {
        for (const [k, v] of Object.entries(items || {})) {
          if (VALID[k]?.(v)) {
            settings[k] = v;
          }
        }

        resolve();
      });
    } catch {
      resolve();
    }
  });

  // a choice made in another tab applies here too
  chrome.storage.onChanged.addListener((changes, area) => {
    let changed = false;

    for (const [k, { newValue }] of Object.entries(area === "local" ? changes : {})) {
      if (VALID[k]?.(newValue) && settings[k] !== newValue) {
        settings[k] = newValue;
        changed = true;
      }
    }

    if (changed) {
      shown?.();
    }
  });

  function set(key, value) {
    settings[key] = value;
    chrome.storage.local.set({ [key]: value });
    shown?.();
  }

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

  // the store's line sample, as in the graph
  function key(store) {
    const k = el("i", { class: "key" });
    k.style.borderColor = color(store);
    k.style.borderTopStyle = STORES[store].dash ? "dashed" : "solid";

    return k;
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
    const svg = el("svg:svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": t().chart });

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
          ...(STORES[s.store].dash ? { "stroke-dasharray": "5 3" } : {}),
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
      const rows = visible.map((s) => [s, priceAt(s, at)]).filter(([, p]) => p != null);

      for (const [s, p] of rows) {
        dots.append(
          el("svg:circle", { cx: x(at), cy: y(p), r: 4, fill: color(s.store), stroke: "var(--surface)", "stroke-width": 2 }),
        );
        tip.append(el("div", { class: "row" }, key(s.store), el("b", {}, euro(p)), el("span", {}, storeName(s.store))));
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

  // a column header that sorts by it, and reverses on the next click
  function sortButton(column, label) {
    const active = settings.sort.replace("-", "") === column;
    const descending = settings.sort.startsWith("-");
    const b = el(
      "button",
      { class: "sort" + (active ? " active" : ""), "aria-sort": active ? (descending ? "descending" : "ascending") : "none" },
      label,
      el("span", { class: "arrow" }, active ? (descending ? "▼" : "▲") : "↕"),
    );
    b.addEventListener("click", () => set("sort", active && !descending ? `-${column}` : column));

    return b;
  }

  function table(result, here) {
    const rows = Object.keys(STORES)
      .filter((s) => result.stores[s])
      .map((s) => [s, result.stores[s]]);
    const column = settings.sort.replace("-", "");
    const descending = settings.sort.startsWith("-");

    if (column === "price") {
      // stores without a price last either way; ties keep the store order
      rows.sort((a, b) => {
        const [pa, pb] = [a[1].price, b[1].price];

        if (pa == null || pb == null) {
          return (pa == null) - (pb == null);
        }

        return descending ? pb - pa : pa - pb;
      });
    } else if (descending) {
      rows.reverse();
    }
    const prices = rows.map(([, s]) => s.price).filter((p) => p != null);
    const cheapest = Math.min(...prices);
    const dearest = Math.max(...prices);
    const herePrice = result.stores[here]?.price;
    const body = el("tbody");

    for (const [store, s] of rows) {
      // the sign of the rounded difference, so 3,71 € against 3,70 € is "0%"
      const pct = Math.round(((s.price - herePrice) / herePrice) * 100);
      const diff = s.price != null && herePrice != null && store !== here ? `${pct > 0 ? "+" : ""}${pct}%` : "";
      // green the cheapest, red the dearest, nothing when they all cost the same
      const rank = s.price == null || cheapest === dearest ? "" : s.price === cheapest ? " cheapest" : s.price === dearest ? " dearest" : "";
      const price = el("td", { class: "num" + rank }, euro(s.price));
      const unit = s.unitPrice != null ? `${euro(s.unitPrice)}/${unitName(s.unit)}${s.unitFixed ? " *" : ""}` : "";
      body.append(
        el(
          "tr",
          { class: store === here ? "here" : "" },
          el("td", {}, key(store), " ", storeName(store)),
          price,
          el("td", { class: "num" }, diff),
          el("td", { class: "num" }, unit),
          s.date
            ? el("td", { class: "num", title: s.date }, t().ago(daysAgo(s.date)))
            : el("td", { class: "num" }, t().notListed),
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
          el("th", {}, sortButton("store", t().store)),
          el("th", { class: "num" }, sortButton("price", t().price)),
          el("th", { class: "num" }, t().vsHere),
          el("th", { class: "num" }, t().unit),
          el("th", { class: "num" }, t().date),
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
    const toggle = el("button", { "aria-label": t().collapse }, state.collapsed ? "▴" : "▾");
    const h = el("header", {}, el("div", { class: "title" }, el("div", { class: "name" }, name), el("div", { class: "sub" }, sub)), toggle);
    h.addEventListener("click", () => {
      state.collapsed = !state.collapsed;
      save();
      p.classList.toggle("collapsed", state.collapsed);
      toggle.textContent = state.collapsed ? "▴" : "▾";
    });
    p.append(h);
  }

  // the last row of the panel: the panel is pinned to the bottom of the
  // window, so its buttons stay under the pointer whatever opens above them
  // or however long the text gets in the other language
  function footer(body, ...left) {
    // shows the language it switches to
    const language = el("button", { class: "lang", "aria-label": t().language, title: t().language }, settings.lang === "el" ? "EN" : "ΕΛ");
    language.addEventListener("click", () => set("lang", settings.lang === "el" ? "en" : "el"));
    body.append(el("div", { class: "footer" }, el("div", {}, ...left), language));
  }

  // the store's cheaper pack sizes of the product, per unit
  function packs(pack, here) {
    const unit = unitName(pack.unit);
    const box = el("div", { class: "packs" }, el("div", { class: "head" }, t().cheaperHere(unit)));

    for (const [code, name, price, unitPrice, multipack] of pack.cheaper) {
      const saving = Math.round(((unitPrice - pack.unit_price) / pack.unit_price) * 100);
      const link = SEARCH[here]
        ? el("a", { href: SEARCH[here](code), target: "_blank", rel: "noopener" }, name)
        : el("span", { class: "what" }, name);
      // cans for a big bottle, or the other way round, may not suit
      const format = multipack === pack.multipack ? "" : multipack ? t().multipack : t().singlePack;
      box.append(
        el(
          "div",
          { class: "alt" },
          el("div", {}, link),
          el(
            "div",
            { class: "meta" },
            el("span", { class: "unit" }, `${euro(unitPrice)}/${unit}`),
            el("span", { class: "save" }, `${saving}%`),
            el("span", { class: "price" }, t().thePack(euro(price))),
            ...(format ? [el("span", { class: "tag" }, format)] : []),
          ),
        ),
      );
    }

    box.append(
      el("div", { class: "note" }, t().thisOne(`${euro(pack.unit_price)}/${unit}`)),
    );

    return box;
  }

  function render(result, here) {
    shown = () => render(result, here);

    if (!result.product) {
      const p = panel();
      header(p, result.pack.name, t().cheaperPack);
      const body = el("div", { class: "body" }, packs(result.pack, here));
      footer(body);
      p.append(body);
      return;
    }

    const p = panel();
    const all = series(result);
    const listed = Object.values(result.stores).filter((s) => s.price != null).length;
    const name = [result.product.name, result.product.size].filter(Boolean).join(" · ");
    header(p, name, t().listed(listed, Object.keys(result.stores).length));
    const body = el("div", { class: "body" });
    p.append(body);

    const ranges = el("div", { class: "ranges" });
    const holder = el("div");

    function draw() {
      holder.replaceChildren(all.length ? chart(all, here) : el("div", { class: "note" }, t().noHistory));
    }

    for (const [label, days] of RANGES) {
      const b = el("button", { "aria-pressed": String(state.range === days) }, t()[label]);
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
      legend.append(el("span", {}, key(s.store), " ", storeName(s.store)));
    }

    if (settings.history) {
      draw();
    }

    if (result.pack) {
      body.append(packs(result.pack, here));
    }

    const showHistory = el(
      "button",
      { class: "toggle", "aria-expanded": String(settings.history) },
      settings.history ? t().hideHistory : t().showHistory,
    );
    showHistory.addEventListener("click", () => {
      set("history", !settings.history);
      // a panel taller than the window scrolls: keep the button in view
      host.shadowRoot.querySelector(".panel").scrollTop = 1e9;
    });
    body.append(table(result, here), el("div", { class: "note" }, t().matched));
    // the stores whose unit price we corrected, marked * in the table
    const fixed = Object.entries(result.stores).filter(([, s]) => s.unitFixed && s.unitPrice != null);

    if (fixed.length) {
      const names = fixed.map(([store]) => storeName(store)).join(", ");
      body.append(el("div", { class: "note" }, t().unitFixed(names)));
    }

    // the graph opens above the button
    if (settings.history) {
      body.append(ranges, holder, legend);
    }

    footer(body, showHistory);
  }

  function message(text) {
    shown = null;
    const p = panel();
    header(p, "ekatanalotis", "");
    const body = el("div", { class: "message body" }, text);
    footer(body);
    p.append(body);
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
      shown = null;
      return;
    }

    try {
      await settingsLoaded;
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
        message(t().error(error.message));
      }
    }
  }

  check();
  // the stores are single page apps: follow navigation
  setInterval(check, 1000);
})();
