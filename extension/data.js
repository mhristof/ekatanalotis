// Loads the files publish.py builds and answers "what does this product
// cost in every store". Shared by the service worker (importScripts) and
// tests that run it in a page.

const DATA_URL = "https://mhristof.github.io/ekatanalotis/";
const STORES = ["kritikos", "ab", "mymarket", "sklavenitis", "xalkiadakis", "marketin", "efresh"];
// products.json and the latest prices are re-read after this long
const MAX_AGE = 60 * 60 * 1000;

let loading = null;

async function getJSON(path) {
  // revalidate: Pages lets browsers keep files for 10 minutes, so a new
  // build could otherwise be missed
  const response = await fetch(DATA_URL + path, { cache: "no-cache" });

  if (!response.ok) {
    throw new Error(`${path}: HTTP ${response.status}`);
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
    // refresh in the background, keep answering from the old data
    loading.then((d) => {
      if (Date.now() - d.loaded > MAX_AGE) {
        loadData().then((fresh) => (loading = Promise.resolve(fresh)), () => {});
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
