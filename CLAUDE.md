# Notes for Claude

## Browser extension (`extension/`) UI rules

These come from the user; keep them when changing the panel.

- **Buttons never move when pressed.** Like Chrome's tab strip, which
  doesn't resize while you close tabs so you can keep clicking the same
  spot: pressing a control must not shift it or the controls next to it.
  - The panel is pinned to the bottom right and grows upwards, so
    controls that change the panel's height or text (the history toggle,
    the language switch) live in the bottom `footer()` row, and anything
    they open goes *above* them.
  - Text that changes with state or language must not move a button
    horizontally either: left-aligned on the left, fixed-size on the right.
  - When adding a control, check its position before and after pressing
    it, in both languages (`getBoundingClientRect()` in the test page
    below).
- **Greek by default**, with an EN/ΕΛ switch. Every user-facing string
  goes in `TEXT` in `content.js`, in both `el` and `en`, store names and
  units included.
- **Settings are remembered** in `chrome.storage.local` (shared by every
  store's site and every tab), not the site's `localStorage`: the user
  must not have to pick them again on another site or after a restart.
- **Latest prices first.** The panel opens with the current prices table;
  the price history graph is behind a toggle, closed by default.
- **Price colours:** in the prices table the cheapest price is green, the
  dearest red (neither when all are the same), and the page's own store's
  row is bold. The colours are text colours with at least 4.5:1 contrast
  on the light and dark panel.
- **Dates are relative** in the panel ("σήμερα", "χθες", "πριν από 3
  ημέρες"), with the ISO date on hover, not the same date on every row.
- **Cache in the browser.** Data files are kept in Cache Storage per build
  (`index.json`'s `updated`); only `index.json` is checked, at most hourly.
  Don't add code that re-downloads the big files on every service worker
  start.

## Testing the extension

Claude can't install the unpacked extension. To test it, serve a page
that runs the real `content.js` and `data.js` with `chrome.storage` and
`chrome.runtime.sendMessage` stand-ins and a fake store `location` (pass
them in with `new Function("chrome", "location", source)`), from
`python3 -m http.server` on 127.0.0.1, and open it with Claude in Chrome.
Chrome blocks store pages from fetching a local server, so the page has
to be served locally, not injected into the store site.
