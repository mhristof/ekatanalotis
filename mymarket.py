import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import json
from bs4 import BeautifulSoup


def extract_product_data(html_content):
    # Function to decode unicode sequences using HTML unescape
    def decode_unicode_escapes(text):
        return html.unescape(text)

    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Initialize lists to store the extracted data
    product_data = []

    # Enhanced logic to find product details using identified patterns

    for article in soup.find_all("article", {"data-controller": "google-analytics"}):
        # Extract product code, name, and price from data attributes
        data_values = article.get("data-google-analytics-item-value")

        if data_values:
            # Replace HTML entities and load as JSON
            data_dict = json.loads(data_values.replace("&quot;", '"'))
            product_code = data_dict.get("id", "N/A")
            product_name = decode_unicode_escapes(data_dict.get("name", "N/A"))
            product_price = float(data_dict.get("price", "N/A"))

            # Round the product price to two decimal places
            rounded_price = round(product_price, 2)

            # Append the product details as a list
            product_data.append([product_code, product_name, f"{rounded_price:.2f}"])

    return product_data


def fetch_page_data(url, page):
    thisURL = f"{url}?page={page}" if page > 1 else url
    response = requests.get(thisURL)

    return response.text, page, url


def mymarket():
    ret = []

    uids = {}
    sections = [
        "frouta-lachanika",
        "fresko-kreas-psari",
        "galaktokomika-eidi-psygeiou",
        "tyria-allantika-deli",
        "katepsygmena-trofima",
        "mpyres-anapsyktika-krasia-pota",
        "proino-rofimata-kafes",
        "artozacharoplasteio-snacks",
        "trofima",
        "frontida-gia-to-moro-sas",
        "prosopiki-frontida",
        "oikiaki-frontida-chartika",
        "kouzina-mikrosyskeves-spiti",
        "frontida-gia-to-katoikidio-sas",
        "epochiaka",
    ]

    with ThreadPoolExecutor(max_workers=10) as executor:
        for section in sections:
            url = f"https://www.mymarket.gr/{section}"

            for i in range(1, 999):
                future = executor.submit(fetch_page_data, url, i)
                html_content, page, url = future.result()
                this = extract_product_data(html_content)

                if len(this) == 0:
                    print(
                        f"No items found on {url}?page={page}, stopping further requests for this section."
                    )

                    break

                ret += this
                print(f"Found {len(this)} items on {url}?page={page}")

    return ret
