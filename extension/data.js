// Loads the files publish.py builds and answers "what does this product
// cost in every store". Shared by the service worker (importScripts) and
// tests that run it in a page.

const DATA_URL = "https://mhristof.github.io/ekatanalotis/";
const STORES = ["kritikos", "ab", "mymarket", "sklavenitis", "xalkiadakis", "marketin", "efresh", "masoutis"];
// index.json is checked for a new build after this long
const MAX_AGE = 60 * 60 * 1000;
// every file is kept in the Cache Storage named after its build, so it is
// downloaded once a build, not every time the service worker starts
const CACHE_PREFIX = "ekatanalotis-";

let loading = null;
// {id: index.json's build time, checked: when}
let build = null;
// the check in flight, shared by the files loaded at once
let checking = null;

async function fetchJSON(path) {
  // revalidate: Pages lets browsers keep files for 10 minutes, so a new
  // build could otherwise be missed
  const response = await fetch(DATA_URL + path, { cache: "no-cache" });

  if (!response.ok) {
    throw new Error(`${path}: HTTP ${response.status}`);
  }

  return response;
}

function currentBuild() {
  if (build && Date.now() - build.checked < MAX_AGE) {
    return Promise.resolve(build.id);
  }

  checking ||= checkBuild().finally(() => (checking = null));

  return checking;
}

async function checkBuild() {
  const cached = (await caches.keys()).filter((n) => n.startsWith(CACHE_PREFIX)).sort();

  try {
    const index = await (await fetchJSON("index.json")).json();
    build = { id: index.updated, checked: Date.now() };
  } catch (error) {
    // offline: answer from the newest build there is
    if (!cached.length) {
      throw error;
    }

    build = { id: cached[cached.length - 1].slice(CACHE_PREFIX.length), checked: Date.now() };
  }

  for (const name of cached) {
    if (name !== CACHE_PREFIX + build.id) {
      await caches.delete(name);
    }
  }

  return build.id;
}

async function getJSON(path) {
  const cache = await caches.open(CACHE_PREFIX + (await currentBuild()));
  let response = await cache.match(DATA_URL + path);

  if (!response) {
    response = await fetchJSON(path);
    await cache.put(DATA_URL + path, response.clone());
  }

  return response.json();
}

async function loadData() {
  const [products, ...perStore] = await Promise.all([
    getJSON("products.json"),
    ...STORES.map((s) => getJSON(`latest/${s}.json`).catch(() => null)),
    ...STORES.map((s) => getJSON(`packs/${s}.json`).catch(() => ({}))),
  ]);
  const latest = perStore.slice(0, STORES.length);
  const packs = perStore.slice(STORES.length);
  // {store: {code: product_id}}
  const ids = {};

  for (const [productId, p] of Object.entries(products)) {
    for (const [store, code] of Object.entries(p.codes)) {
      (ids[store] ||= {})[code] = productId;
    }
  }

  return {
    loaded: Date.now(),
    products,
    ids,
    latest: Object.fromEntries(STORES.map((s, i) => [s, latest[i]]).filter(([, l]) => l)),
    packs: Object.fromEntries(STORES.map((s, i) => [s, packs[i]])),
  };
}

function data() {
  if (!loading) {
    loading = loadData().catch((error) => {
      loading = null;
      throw error;
    });
  } else {
    // refresh in the background when there is a new build, keep answering
    // from the old data
    loading.then((d) => {
      if (Date.now() - d.loaded > MAX_AGE) {
        d.loaded = Date.now();
        const old = build?.id;
        currentBuild()
          .then((id) => (id !== old ? loadData() : null))
          .then((fresh) => fresh && (loading = Promise.resolve(fresh)), () => {});
      }
    });
  }

  return loading;
}

// {productId, product, stores: {store: {code, price, unitPrice, unit, date,
// history}}, pack}: product and stores when the code is matched to another
// store, pack ({name, unit, unit_price, multipack, cheaper}) when the store
// has a cheaper pack size of it; null when neither
async function lookup(store, code) {
  const d = await data();
  const productId = d.ids[store]?.[code];
  const pack = d.packs[store]?.[code] || null;

  if (!productId) {
    return pack && { pack };
  }

  const product = d.products[productId];
  const history = await getJSON(`history/${productId}.json`).catch(() => ({}));
  const stores = {};

  for (const [s, c] of Object.entries(product.codes)) {
    const latest = d.latest[s];
    const [price, unitPrice, unit] = latest?.prices[c] || [];
    stores[s] = {
      code: c,
      price: price ?? null,
      unitPrice: unitPrice ?? null,
      unit: unit ?? null,
      // the price date, null when the latest scrape didn't list it
      date: price == null ? null : latest.date,
      history: history[s] || [],
    };
  }

  return { productId, product, stores, pack };
}
