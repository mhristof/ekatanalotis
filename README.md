
## gpt promt

```
Write a Python script that fetches product details from multiple sections of the e-fresh website (https://www.e-fresh.gr/en/). The script should:

Fetch product details from sections: groceries, drinks, personal-care, baby, household, clothing, home, biologika-proionta-bio-corner, vegan-shop.
Use multithreading to fetch pages concurrently within each section.
Include retry logic to handle requests.exceptions.ConnectionError using the tenacity library.
Use a requests.Session with an HTTPAdapter for robust request handling.
Print the URL being processed and the number of products found on each page.
```
