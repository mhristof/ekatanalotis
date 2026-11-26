# Chrome Web Store listing

What to paste into the Developer Dashboard
(https://chrome.google.com/webstore/devconsole). The package is
`make extension-zip` (`dist/ekatanalotis-<version>.zip`); raise `version`
in `extension/manifest.json` before every upload.

The name and short description come from `extension/_locales/` (Greek is
the default language, English the other).

## Store listing

Don't list the supermarkets' names in the description: review rejected
1.0.0 for "excessive keywords" over the list of all 8 (violation "Yellow
Argon"). Naming the 3 sites the extension runs on is fine.

- **Category:** Shopping
- **Language:** Greek (add English as a second language for the
  description below)
- **Icon:** `extension/icons/icon128.png`
- **Screenshots** (1280×800): `store/screenshot-*.png`

### Description (Greek)

Δείτε αμέσως αν ένα προϊόν κοστίζει λιγότερο σε άλλο σούπερ μάρκετ.

Στη σελίδα ενός προϊόντος στο Σκλαβενίτης, στο ΑΒ ή στο Μασούτης, το
ekatanalotis δείχνει ένα μικρό πλαίσιο με:

- την τιμή του ίδιου προϊόντος σε 8 ελληνικά σούπερ μάρκετ, με πράσινο
  τη φθηνότερη και κόκκινο την ακριβότερη
- την τιμή ανά κιλό ή λίτρο
- φθηνότερες συσκευασίες του ίδιου προϊόντος στο ίδιο κατάστημα
- το ιστορικό τιμών σε γράφημα, αν το ανοίξετε

Οι τιμές ενημερώνονται κάθε μέρα. Τα προϊόντα αντιστοιχίζονται με
barcode ή με το όνομα, οπότε ελέγξτε το μέγεθος πριν αλλάξετε
κατάστημα. Η επέκταση δεν συλλέγει δεδομένα και δεν έχει διαφημίσεις.

### Description (English)

See at a glance whether a product costs less in another supermarket.

On a product's page at Sklavenitis, AB or Masoutis, ekatanalotis shows a
small panel with:

- the same product's price in 8 Greek supermarkets, the cheapest in
  green and the dearest in red
- the price per kg or litre
- cheaper pack sizes of the same product in the same store
- the price history graph, when you open it

Prices are updated daily. Products are matched by barcode or by name, so
check the size before you switch store. The extension collects no data
and has no ads.

## Privacy practices

### Single purpose

Shows, on a supermarket's product page, the same product's current price
in other Greek supermarkets.

### Permission justifications

- **storage:** keeps the user's settings (language, table sort order,
  whether the price history graph is shown) so they apply on every
  supported site and after a restart.
- **Host permission `https://mhristof.github.io/*`:** downloads the
  public daily price files the panel shows, published by this project on
  GitHub Pages.
- **Content scripts on `www.sklavenitis.gr`, `www.ab.gr`,
  `www.masoutis.gr`:** reads the product code of the product page the
  user is on and shows the price panel on that page. Nothing on the page
  is changed or sent anywhere.

### Remote code

No, the extension doesn't use remote code. It downloads JSON data only.

### Data usage

Collects none of the listed data types. Check the three certifications
(not sold to third parties, not used for unrelated purposes, not used
for creditworthiness or lending).

### Privacy policy URL

https://mhristof.github.io/ekatanalotis/privacy.html
