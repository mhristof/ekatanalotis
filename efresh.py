import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import net


def fetch_page(url):
    return net.get_text(url)


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


def fetch_section_pages(section, max_workers=10, max_pages=None):
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

            if len(page_futures) >= max_workers or page_number > (max_pages or page_number):
                break

        while page_futures:
            future = page_futures.pop(0)
            page_content = future.result()
            products = extract_product_details(page_content)
            print(f"Found {len(products)} products on a fetched page")

            if not products:
                break  # Exit loop if no products found
            all_products.extend(products)

            if max_pages and page_number > max_pages:
                continue

            # Queue next page
            url = f"{base_url}?page={page_number}"
            print(f"Queueing URL: {url}")
            page_futures.append(executor.submit(fetch_page, url))
            page_number += 1

    return all_products


SECTIONS = [
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


def efresh(sections=None, max_pages=None):
    sections = sections or SECTIONS
    all_products = []

    # Use ThreadPoolExecutor to fetch sections concurrently
    with ThreadPoolExecutor(max_workers=len(sections)) as executor:
        futures = [
            executor.submit(fetch_section_pages, section, max_pages=max_pages)
            for section in sections
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
