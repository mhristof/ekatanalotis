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

from mymarket import mymarket
from efresh import efresh
from sklavenitis import sklavenitis
from ab import ab
from kritikos import kritikos
from marketin import marketin
from xalkiadakis import xalkiadakis

# masoyti, galaxias, egnatia, bazaar, lidl, discount_markt are not scraped yet
STORES = {
    "marketin": marketin,
    "kritikos": kritikos,
    "xalkiadakis": xalkiadakis,
    "mymarket": mymarket,
    "efresh": efresh,
    "sklavenitis": sklavenitis,
    "ab": ab,
}


def save_to_file(sms, today):
    # smdata/ is not checked out in CI (sparse checkout)
    os.makedirs("smdata", exist_ok=True)

    for sm, data in sms.items():
        # sorted and without exact duplicates (stores list products in
        # more than one section) so that day-to-day diffs stay small
        lines = sorted(
            {f"{today},{item[0]},{item[1].replace(',', '-')},{item[2]}\n" for item in data},
            key=lambda line: line.split(",", 2)[1],
        )

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
    """Drop stores that returned no or suspiciously few rows; return the
    names of the stores that failed."""
    failed = []

    for sm, data in list(sms.items()):
        prev = previous_count(sm, today)
        print(f"{sm}: {len(data)} rows, previous: {prev}")

        if not data or (prev and len(data) < prev * MIN_ROWS_RATIO):
            print(f"error in {sm}: got {len(data)} rows, previous run had {prev}")
            failed.append(sm)
            del sms[sm]

    return failed


def insert_all():
    sms = {}

    for sm, func in STORES.items():
        try:
            sms[sm] = func()
        except Exception as e:
            print(f"error in {sm}: {e}")
            sms[sm] = []

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    failed = validate(sms, today)
    save_to_file(sms, today)

    return failed


def main():
    failed = insert_all()

    if failed:
        print(f"failed stores: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
