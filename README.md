# ekatanalotis

Daily supermarket prices, scraped by `.github/workflows/schedule.yml` and
committed to `smdata/<store>-<YYYY-MM-DD>.csv` as `date,code,name,price`
rows, sorted by code.

## Layout

- `sm.py` - runs every store in `STORES`, drops failed scrapes (no rows,
  or under half of the previous run), writes the csv files and prints a
  summary. Exits non-zero if any store failed.
- `<store>.py` - one module per store: `SECTIONS`, `fetch_page(section, page)`
  and `parse()`.
- `net.py` - shared HTTP session (retries, timeouts, user agent) and the
  `paginate`/`crawl` helpers that fetch pages and sections concurrently.

## Running

```
pip install -r requirements-dev.txt
make run            # scrape everything into smdata/
make test           # smoke-test every store: one section, one page
make test-offline   # only the tests that don't hit the network
```
