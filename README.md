# ekatanalotis

Daily supermarket prices, scraped by `.github/workflows/schedule.yml` and
committed to `smdata/<store>-<YYYY-MM-DD>.csv` as `date,code,name,price`
rows, sorted by code.

Product details for matching products across stores are kept in
`catalog/<store>.csv` as `code,name,brand,category,size,unit,unit_price,ean`
rows: one per product code ever seen, updated in place by every run.
`unit` is `kg`, `l`, `piece`, `wash` or `m`, the unit `unit_price` is
per. Stores may add their own fields after these (efresh's `slug`). Only
kritikos lists barcodes (`ean`, `;` separated, old and multipack ones
included); ab and mymarket find products by EAN in their site search.

## Layout

- `sm.py` - runs every store in `STORES`, drops failed scrapes (no rows,
  or under half of the previous run), writes the csv files and prints a
  summary. Exits non-zero if any store failed.
- `<store>.py` - one module per store: `SECTIONS`, `fetch_page(section, page)`
  and `parse()`. masoutis' api takes POSTs with an anonymous visitor's
  credentials (`GetCred`) and the site's fixed `PassKey`.
- `slow.py` - stores whose bot protection only allows a trickle of
  requests (xalkiadakis). `.github/workflows/slow.yml` runs hourly and
  scrapes the next 2 sections into `pending/` on a `data/<store>-<day>`
  branch; the first run of the next day folds it into one commit on main
  (`smdata/<store>-<day>.csv`) and deletes the branch
  (`scripts/slow_store.sh`).
- `catalog.py` - reads, merges and writes `catalog/`; fetchers return
  `[code, name, price, details]` rows and the price csv uses the first
  three.
- `match.py` - matches kritikos products to ab and mymarket by EAN.
  `python match.py search [--limit N]` searches the store sites for EANs
  not searched before (live, one search per 1.5 s per store) and appends
  the results to `matches/ean_search.csv`; `python match.py accept`
  (offline) checks the hits by size and brand and writes
  `matches/ean_matches.csv` and `matches/ean_candidates.csv` for review.
- `fuzzy.py` - matches products of all stores by name, brand and size,
  offline. `python fuzzy.py match` adds them to the EAN matches and writes
  `matches/matches.csv` (`product_id,store,code,method,score`, one code
  per store per product, `method` is `ean` or `fuzzy`). The scorer is a
  logistic regression trained on the EAN matches: `python fuzzy.py train`
  fits it, reports precision and recall on held-out EAN matches and writes
  `matches/fuzzy_weights.json`. efresh names are in English, so efresh's
  catalog also keeps the product's `slug`, its Greek name in Latin letters.
- `publish.py` - `python publish.py build` writes the browser extension's
  files under `site/`: `latest/<store>.json` (every code in the store's
  latest price file: price, unit price, unit), `products.json` (the
  matched products: name, brand, size and the code in each store) and
  `index.json` (build time, each store's price date) and
  `history/<product_id>.json` (each store's price changes of a matched
  product). `python publish.py history` adds the price files not seen
  before to `history/<store>.csv` (`code,date,price`, one row per price
  change; `history/dates.json` has the last date added per store), so
  the build doesn't need all of `smdata/`.
- `packs.py` - cheaper pack sizes of the same product in the same store
  (same name once sizes are taken out, unit price from price and pack
  size), published by `publish.py build` as `packs/<store>.json`.
- `extension/` - Chrome extension (Manifest V3). On a sklavenitis or ab
  product page it shows a panel with the product's price history and
  latest price in every store it is matched in, and the store's cheaper
  pack sizes of it, read from the GitHub
  Pages files. Install with chrome://extensions, Developer mode, "Load
  unpacked", and pick `extension/`.
- `net.py` - shared HTTP session (retries, timeouts, user agent) and the
  `paginate`/`crawl` helpers that fetch pages and sections concurrently.

## CI

- `schedule.yml` (daily): all stores on github runners, except sklavenitis
  which runs on the self-hosted runner, as its site blocks github IPs.
- `slow.yml` (hourly): xalkiadakis on the self-hosted runner.
- `publish.yml` (after `schedule.yml`): searches the EANs of new kritikos
  products, re-runs the matching, commits `matches/` and `history/` and
  publishes
  `publish.py build`'s files on GitHub Pages
  (https://mhristof.github.io/ekatanalotis/).
- `test.yml`: tests on branches and pull requests, github runners only.

Both scrape jobs commit `smdata/` and `catalog/` through
`scripts/commit_push.sh`.

The scrape workflows have no `schedule:` trigger, as github ran them hours
late or not at all. A cron on `mikestuff` (user `mike`, `gh` logged in with
a fine-grained token with Actions: read and write on this repo) dispatches
them instead:

```
7 * * * *   /usr/bin/gh workflow run slow.yml     -R mhristof/ekatanalotis --ref main >> $HOME/.cache/ekatanalotis/cron.log 2>&1
12 12 * * * /usr/bin/gh workflow run schedule.yml -R mhristof/ekatanalotis --ref main >> $HOME/.cache/ekatanalotis/cron.log 2>&1
```

## Running

```
pip install -r requirements-dev.txt
make run            # scrape everything into smdata/
make test           # smoke-test every store: one section, one page
make test-offline   # only the tests that don't hit the network
```
