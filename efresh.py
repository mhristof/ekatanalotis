import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

# Set up a requests session with retry logic
session = requests.Session()
retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"],
    backoff_factor=2,
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)


# Retry decorator for handling connection errors
@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(requests.exceptions.ConnectionError),
)
def fetch_page(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = session.get(url, headers=headers)
    response.raise_for_status()

    return response.text


def extract_product_details(page_content):
    # Define refined regex patterns for product code, name, and price
    product_pattern = re.compile(
        r'{"kodikos":"(?P<code>\d{10})","title":"(?P<name>[^"]+)".*?"price":(?P<price>\d+\.\d{2})',
        re.DOTALL,
    )

    # Find all matches in the data
    matches = product_pattern.finditer(page_content)

    # Extract the product details
    products = []

    for match in matches:
        products.append(
            [match.group("code"), match.group("name"), float(match.group("price"))]
        )

    return products


def fetch_section_pages(section, max_workers=10):
    base_url = f"https://www.e-fresh.gr/en/{section}"
    all_products = []
    page_number = 1
    page_futures = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while True:
            url = f"{base_url}?page={page_number}"
            print(f"Queueing URL: {url}")
            page_futures.append(executor.submit(fetch_page, url))
            page_number += 1

            if len(page_futures) >= max_workers:
                break

        while page_futures:
            future = page_futures.pop(0)
            page_content = future.result()
            products = extract_product_details(page_content)
            print(f"Found {len(products)} products on a fetched page")

            if not products:
                break  # Exit loop if no products found
            all_products.extend(products)

            # Queue next page
            url = f"{base_url}?page={page_number}"
            print(f"Queueing URL: {url}")
            page_futures.append(executor.submit(fetch_page, url))
            page_number += 1

    return all_products


def efresh():
    sections = [
        "groceries",
        "drinks",
        "personal-care",
        "baby",
        "household",
        "clothing",
        "home",
        "biologika-proionta-bio-corner",
        "vegan-shop",
    ]

    all_products = []

    # Use ThreadPoolExecutor to fetch sections concurrently
    with ThreadPoolExecutor(max_workers=len(sections)) as executor:
        futures = [
            executor.submit(fetch_section_pages, section) for section in sections
        ]

        for future in as_completed(futures):
            all_products.extend(future.result())

    return all_products


# Example usage

if __name__ == "__main__":
    all_products = efresh()

    # Print the extracted products

    for product in all_products:
        print(product)
