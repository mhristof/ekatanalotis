import subprocess
from bs4 import BeautifulSoup
import concurrent.futures
import re


# Define the URLs to fetch product details from
urls = [
    "https://www.sklavenitis.gr/eidi-artozacharoplasteioy/",
    "https://www.sklavenitis.gr/freska-froyta-lachanika/",
    "https://www.sklavenitis.gr/fresko-psari-thalassina/",
    "https://www.sklavenitis.gr/fresko-kreas/",
    "https://www.sklavenitis.gr/galata-rofimata-chymoi-psygeioy/",
    "https://www.sklavenitis.gr/giaoyrtia-kremes-galaktos-epidorpia-psygeioy/",
    "https://www.sklavenitis.gr/turokomika-futika-anapliromata/",
    "https://www.sklavenitis.gr/ayga-voytyro-nopes-zymes-zomoi/",
    "https://www.sklavenitis.gr/allantika/",
    "https://www.sklavenitis.gr/orektika-delicatessen/",
    "https://www.sklavenitis.gr/etoima-geymata/",
    "https://www.sklavenitis.gr/katepsygmena/",
    "https://www.sklavenitis.gr/kava/",
    "https://www.sklavenitis.gr/anapsyktika-nera-chymoi/",
    "https://www.sklavenitis.gr/xiroi-karpoi-snak/",
    "https://www.sklavenitis.gr/mpiskota-sokolates-zacharodi/",
    "https://www.sklavenitis.gr/eidi-proinoy-rofimata/",
    "https://www.sklavenitis.gr/vrefikes-paidikes-trofes/",
    "https://www.sklavenitis.gr/trofima-pantopoleioy/",
    "https://www.sklavenitis.gr/trofes-eidi-gia-katoikidia/",
    "https://www.sklavenitis.gr/eidi-mias-chrisis-eidi-parti/",
    "https://www.sklavenitis.gr/chartika-panes-servietes/",
    "https://www.sklavenitis.gr/kallyntika-eidi-prosopikis-ygieinis/",
    "https://www.sklavenitis.gr/aporrypantika-eidi-katharismoy/",
    "https://www.sklavenitis.gr/eidi-oikiakis-chrisis/",
]

# Curl command template
curl_command_template = [
    "curl",
    "-H",
    "user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "--compressed",
]


# Function to fetch page content using curl
def fetch_page(url):
    command = curl_command_template + [url]
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode == 0:
        return result.stdout
    else:
        print(f"Error fetching {url}: {result.stderr}")

        return ""


# Extract product details using BeautifulSoup
def extract_product_details(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    products = []
    pattern = re.compile(
        r"data-plugin-analyticsimpressions=.*?{&quot;item_id&quot;:&quot;(\d+)&quot;,&quot;item_name&quot;:&quot;(.*?)&quot;.*?price&quot;:(\d+\.\d+)",
        re.DOTALL,
    )
    matches = pattern.findall(html_content)

    for match in matches:
        product_code, product_name, product_price = match
        products.append([product_code, product_name, float(product_price)])

    return products


# Function to process a single URL and fetch all pages
def process_url(base_url):
    page = 1
    all_products = []

    while True:
        url = f"{base_url}?pg={page}"
        print(f"Processing URL: {url}")
        html_content = fetch_page(url)
        products = extract_product_details(html_content)
        print(f"Found {len(products)} products on page {page}")

        if len(products) == 0:
            break
        all_products.extend(products)
        page += 1

    return all_products


# Multithreading to process URLs concurrently
def sklavenitis():
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_url, url): url for url in urls}

        for future in concurrent.futures.as_completed(futures):
            try:
                products = future.result()
                all_results.extend(products)
                print(f"Finished processing URL with {len(products)} products found.")
            except Exception as e:
                print(f"Error processing URL: {e}")

    return all_results


def main():
    return sklavenitis()


if __name__ == "__main__":
    all_products = main()
    # all_products is a list of lists containing product details
    print(all_products)
