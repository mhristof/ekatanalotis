#! /usr/bin/env python3
"""Divide the price of kritikos csv files written with the /10 bug
(a7d9312, 2024-11-13 .. 6365f8a) by 10.

A file is only touched when its median price is above MEDIAN_LIMIT
(correct files are ~2.7, buggy ones ~27), so re-running is safe, e.g.
after merging, for files CI wrote with the old code meanwhile."""

import glob
import statistics

MEDIAN_LIMIT = 10


def fix(line):
    rest, price = line.rstrip("\n").rsplit(",", 1)
    # same value the fixed kritikos.parse writes: finalPrice (cents) / 100
    cents = round(float(price) * 10)

    return f"{rest},{cents / 100}\n"


def main():
    fixed = 0

    for path in sorted(glob.glob("smdata/kritikos-*.csv")):
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            continue

        if statistics.median(float(l.rsplit(",", 1)[1]) for l in lines) <= MEDIAN_LIMIT:
            continue

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(fix(l) for l in lines)

        fixed += 1

    print(f"fixed {fixed} files")


if __name__ == "__main__":
    main()
