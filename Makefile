.PHONY: run test test-offline

# scrape all stores and write today's csv files to smdata/
run:
	python -u ./sm.py

# smoke-test every fetcher against the live sites (one section, one page)
test:
	python -m pytest -v

test-offline:
	python -m pytest -v -m "not network"
