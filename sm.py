#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""

"""

import os
import subprocess
import sys
import datetime
import time
from concurrent.futures import ThreadPoolExecutor

from mymarket import mymarket
from efresh import efresh
from sklavenitis import sklavenitis
from ab import ab
from kritikos import kritikos
from marketin import marketin

# masoyti, galaxias, egnatia, bazaar, lidl, discount_markt are not scraped yet;
# xalkiadakis is scraped a few sections per hour, see slow.py
STORES = {
    "marketin": marketin,
    "kritikos": kritikos,
    "mymarket": mymarket,
    "efresh": efresh,
    "sklavenitis": sklavenitis,
    "ab": ab,
}


def sort_lines(lines):
    """Sorted by code and without exact duplicates (stores list products in
    more than one section) so that day-to-day diffs stay small."""
    return sorted(set(lines), key=lambda line: line.split(",", 2)[1])


def csv_lines(data, today):
    return sort_lines(
        f"{today},{item[0]},{item[1].replace(',', '-')},{item[2]}\n" for item in data
    )


def save_to_file(sms, today):
    # smdata/ is not checked out in CI (sparse checkout)
    os.makedirs("smdata", exist_ok=True)

    for sm, data in sms.items():
        lines = csv_lines(data, today)

        with open(f"smdata/{sm}-{today}.csv", "w") as f:
            f.writelines(lines)
            print(f"saved {len(lines)} items to {sm}.csv")


# a store returning less than this fraction of its previous row count is
# treated as a failed scrape
MIN_ROWS_RATIO = 0.5


def previous_count(sm, today):
    """Row count of the most recent non-empty csv for sm before today.

    Read through git so it works on the sparse CI checkout, where smdata/
    is not in the working tree; only the blobs read are fetched."""
    try:
        names = subprocess.run(
            ["git", "ls-tree", "--name-only", "HEAD", "smdata/"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return None

    names = sorted(
        n for n in names if n.startswith(f"smdata/{sm}-2") and n < f"smdata/{sm}-{today}"
    )

    for name in reversed(names[-30:]):
        data = subprocess.run(
            ["git", "show", f"HEAD:{name}"], capture_output=True, text=True
        ).stdout

        if data:
            return data.count("\n")

    return None


def validate(sms, today):
    """Drop stores that returned no or suspiciously few rows.

    Returns {store: (rows, previous rows, ok)} for the summary."""
    report = {}

    for sm, data in list(sms.items()):
        prev = previous_count(sm, today)
        ok = bool(data) and not (prev and len(data) < prev * MIN_ROWS_RATIO)
        report[sm] = (len(data), prev, ok)

        if not ok:
            print(f"error in {sm}: got {len(data)} rows, previous run had {prev}")
            del sms[sm]

    return report


def summary(report, durations):
    lines = [f"{'store':<12} {'rows':>7} {'previous':>8} {'change':>7} {'time':>6}  status"]

    for sm, (rows, prev, ok) in report.items():
        change = f"{(rows - prev) / prev * 100:+.1f}%" if prev else "-"
        lines.append(
            f"{sm:<12} {rows:>7} {prev or '-':>8} {change:>7} {durations[sm]:>5.0f}s  {'ok' if ok else 'FAILED'}"
        )

    return "\n".join(lines)


def insert_all():
    def fetch(sm):
        start = time.monotonic()

        try:
            return STORES[sm]()
        except Exception as e:
            print(f"error in {sm}: {e!r}")

            return []
        finally:
            durations[sm] = time.monotonic() - start

    durations = {}

    # every store is a different site, so run them all at once
    with ThreadPoolExecutor(len(STORES)) as executor:
        sms = dict(zip(STORES, executor.map(fetch, STORES)))

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    report = validate(sms, today)
    save_to_file(sms, today)
    print(summary(report, durations))

    return [sm for sm, (_, _, ok) in report.items() if not ok]


def main():
    failed = insert_all()

    if failed:
        print(f"failed stores: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
