from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import visibility_of_element_located
from bs4 import BeautifulSoup
import datetime
import asyncio
import json
import os
import argparse
from sm import insert_all
from click import clickhouse
import time
from functools import cache
from tabulate import tabulate


def fetch(url, until="products-barcode-text"):
    # Set Chrome options
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--window-size=1920,1080")

    browser = webdriver.Chrome(options=chrome_options)

    browser.get(url)

    try:
        title = (
            WebDriverWait(driver=browser, timeout=20)
            .until(visibility_of_element_located((By.CLASS_NAME, until)))
            .text
        )
    except:
        print(f"Element with class {until} not found for url {url}")

        return None
    # retrieve fully rendered HTML content
    content = browser.page_source
    browser.close()

    # we then could parse it with beautifulsoup

    return BeautifulSoup(content, "html.parser")


async def async_prices(step=10):
    ch = clickhouse()

    today = datetime.date.today().strftime("%Y-%m-%d")
    time_now = datetime.datetime.now().strftime("%H:%M:%S")

    if time_now < "11:00:00":
        today = (datetime.date.today() - datetime.timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
        print("Time is before 11:00, fetching data for yesterday: ", today)

    skip_list = [
        x[0]
        for x in ch.query(f"select id from prices where date = '{today}'").result_rows
    ]

    print("Skip list size: ", len(skip_list))

    for i in range(1, 2939, step):  # Increment by 10
        tasks = []

        start_time = datetime.datetime.now()

        for j in range(i, min(i + step, 2939)):  # Create 10 asynchronous tasks
            if j in skip_list:
                continue
            url = f"https://e-katanalotis.gov.gr/product/{j}"
            tasks.append(prices(url))

        results = await asyncio.gather(*tasks)  # Run the tasks concurrently

        finish_time = datetime.datetime.now()

        if not results:
            continue

        save_data(ch, results)
        print(
            f"Saved data for products {i} to {min(i + step - 1, 2938)} in {finish_time - start_time}"
        )


def sanitise():
    ch = clickhouse()

    today = datetime.date.today().strftime("%Y-%m-%d")
    data = ch.query(f"select id, name from prices where date = '{today}'").result_rows

    ids = {}

    for row in data:
        print("name: ", row[1], "hash: ", int_hash_from_string(row[1]))
        ids[row[0]] = row[1]

    print(json.dumps(ids, indent=4))


def int_hash_from_string(s):
    # always return a positive number

    return abs(hash(s)) % (10**8)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--step", type=int, default=10)
    parser.add_argument("-l", "--loop", action="store_true", default=False)
    parser.add_argument("-i", "--info", action="store_true", default=False)
    args = parser.parse_args()

    migrations()

    print("args: ", args)

    if args.info:
        info()

        return

    while True:
        insert_all()
        asyncio.run(async_prices(args.step))

        time.sleep(3600)


def info():
    ch = clickhouse()

    tables = ch.query("show tables").result_rows

    ret = []

    for table in tables:
        table = table[0]

        if table in ["migrations"]:
            continue

        data = [table]

        for date in ["today()", "today() - 1", "today() - 2"]:
            count = ch.query(
                f"select count(*) from {table} where date == {date}"
            ).result_rows[0][0]
            data.append(count)

            if date == "today()":
                continue
            previous_date = data[-2]

            if previous_date == 0:
                data.append(0)

                continue

            data.append(round((count - previous_date) / previous_date * 100, 2))
        ret.append(data)

    # pretty print the table (not json)
    print(
        tabulate(
            ret,
            headers=[
                "table",
                "today",
                "yesterday",
                "change %",
                "day before",
                "change %",
            ],
            tablefmt="pretty",
        )
    )


@cache
def fetch_table(date):
    ch = clickhouse()

    data = ch.query(f"SELECT * FROM prices where date = {date}").result_rows
    columns = [x[0] for x in ch.query("describe prices").result_rows]

    ret = {}

    for row in data:
        newdata = dict(zip(columns, [value for value in row]))

        ret[newdata["barcode"]] = newdata

    return ret


def update_percentages():
    ch = clickhouse()

    data = fetch_table("today() - 1")
    yesterday = fetch_table("yesterday() - 3")

    print("today: ", len(data), "yesterday: ", len(yesterday))

    new_data = {}

    for barcode, data in data.items():
        print("barcode: ", barcode, "data: ", data)

        pct = {
            "barcode": barcode,
        }

        ydata = yesterday.get(barcode, {})

        if not ydata:
            continue

        for k, v in data.items():
            if k in ["id", "name", "url", "date", "barcode"]:
                continue

            try:
                pct[k + "_pct"] = (v - ydata[k]) / ydata[k] * 100
            except:
                pct[k + "_pct"] = 0

        new_data[barcode] = pct

    print("new_data: ", json.dumps(new_data, indent=4))


def migrations():
    ch = clickhouse()
    try:
        current_version = ch.query("select max(version) from migrations").result_rows[
            0
        ][0]
    except:
        current_version = -1

    sql = [
        # create version table
        """ CREATE TABLE IF NOT EXISTS migrations (version UInt32) ENGINE = MergeTree() ORDER BY version """,
        # add barcode column
        """ ALTER TABLE prices ADD COLUMN barcode UInt32 """,
        # make barcode a string
        """ ALTER TABLE prices MODIFY COLUMN barcode String """,
        # create prices_pct table
        """ CREATE TABLE IF NOT EXISTS prices_pct (date Date, barcode String) ENGINE = MergeTree() ORDER BY (date, barcode) """,
    ]

    for i in range(current_version + 1, len(sql)):
        ch.query(sql[i])
        ch.query(f"INSERT INTO migrations VALUES ({i})")
        print(f"Migration {i} executed {sql[i]}")


def save_data(ch, data):
    try:
        columns = list(set().union(*(d.keys() for d in data)))
    except:
        print("error getting columns for data: ", data)

        return

    for x in ["id", "name", "url", "date"]:
        columns.remove(x)

    tables = ch.query("select * from system.tables where name = 'prices'").result_rows

    if not tables:
        cols = ", ".join([f"{col} Float32" for col in columns])
        # set date, id as primary key
        query = f"CREATE TABLE prices (date Date, id UInt32, name String, {cols}, url String) ENGINE = MergeTree() ORDER BY (date, id)"
        print(query)
        ch.query(query)
    else:
        live_columns = [x[0] for x in ch.query("describe prices").result_rows]
        live_pct_columns = [x[0] for x in ch.query("describe prices_pct").result_rows]

        for col in columns:
            if col not in live_columns:
                q = f"ALTER TABLE prices ADD COLUMN {col} Float32"
                print(q)
                ch.query(q)

            if f"{col}_pct" not in live_pct_columns:
                q = f"ALTER TABLE prices_pct ADD COLUMN {col}_pct Float32"
                print(q)
                ch.query(q)

    yesterday = fetch_table("today() - 1")

    for row in data:
        if not row:
            continue

        barcode = row["barcode"]

        qpct = create_query_pct(row, yesterday.get(barcode, {}))
        try:
            ch.query(qpct)
        except:
            print("error inserting pct: ", qpct)

        ch.query(f"INSERT INTO prices FORMAT JSONEachRow {json.dumps(row, indent=4)}")


def create_query_pct(today, yesterday):
    ret = {
        "barcode": today["barcode"],
        "date": today["date"],
    }

    for k, v in today.items():
        if k in ["id", "name", "url", "date", "barcode"]:
            continue

        val = round(yesterday.get(k, 0), 2)

        if val == 0:
            ret[k + "_pct"] = 0

            continue

        ret[k + "_pct"] = (v - val) / val * 100

    return f"INSERT INTO prices_pct FORMAT JSONEachRow {json.dumps(ret, indent=4)}"


async def prices(url):
    soup = fetch(url)

    if not soup:
        return None

    product_name = soup.find("p", class_="product-name").text

    all_market_names = soup.find_all("span", class_="product-market-name")

    barcode = soup.find("p", class_="products-barcode-text").text.split(":")[1].strip()
    today = datetime.date.today().strftime("%Y-%m-%d")

    product_name_en = greek_to_greeklish(product_name)

    ret = {
        "name": product_name_en,
        "url": url,
        "date": today,
        "id": int(os.path.basename(url)),
        "barcode": barcode,
    }

    for market in all_market_names:
        product_price_number = market.find_next_sibling(
            "span", class_="product-price-number"
        ).text
        # strip the € sign
        product_price_number = product_price_number.strip("€")
        # convert greek to english

        # two digits after the decimal point
        ret[greek_to_greeklish(market.text).replace(" ", "_").lower()] = round(
            float(product_price_number), 2
        )

    return ret


@cache
def greek_to_greeklish(text):
    greek_letters = {
        "α": "a",
        "ά": "a",
        "β": "v",
        "γ": "g",
        "δ": "d",
        "ε": "e",
        "έ": "e",
        "ζ": "z",
        "η": "i",
        "ή": "i",
        "θ": "th",
        "ι": "i",
        "ί": "i",
        "κ": "k",
        "λ": "l",
        "μ": "m",
        "ν": "n",
        "ξ": "x",
        "ο": "o",
        "ό": "o",
        "π": "p",
        "ρ": "r",
        "σ": "s",
        "ς": "s",
        "τ": "t",
        "υ": "y",
        "ύ": "y",
        "φ": "f",
        "χ": "ch",
        "ψ": "ps",
        "ω": "o",
        "ώ": "o",
    }

    greeklish_text = ""

    for char in text:
        if char.lower() in greek_letters:
            greeklish_text += greek_letters[char.lower()]
        else:
            greeklish_text += char

    return greeklish_text


if __name__ == "__main__":
    main()
