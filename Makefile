.PHONY: run test test-offline extension-zip

# scrape all stores and write today's csv files to smdata/
run:
	python -u ./sm.py

# smoke-test every fetcher against the live sites (one section, one page)
test:
	python -m pytest -v

test-offline:
	python -m pytest -v -m "not network"

# the Chrome Web Store upload: extension/ zipped with manifest.json at the
# top, named after the manifest's version
EXTENSION_VERSION = $(shell python3 -c 'import json; print(json.load(open("extension/manifest.json"))["version"])')

extension-zip:
	mkdir -p dist
	rm -f dist/ekatanalotis-$(EXTENSION_VERSION).zip
	cd extension && zip -r -X ../dist/ekatanalotis-$(EXTENSION_VERSION).zip . -x '.*' '*/.*'
