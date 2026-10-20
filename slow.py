#! /usr/bin/env python3
"""Stores whose bot protection only allows a trickle of requests.

Every hourly run of .github/workflows/slow.yml scrapes the next few
sections of the day into pending/ on the data/<store>-<date> branch
(`scrape`). Once the day is over the pending csv is checked like any other
store and moved to smdata/ as a single commit on main (`finalize`), see
scripts/slow_store.sh."""

import argparse
import datetime
import importlib
import os
import sys

import net
import sm

SECTIONS_PER_RUN = 2


def paths(store, day):
    return f"pending/{store}-{day}.csv", f"pending/{store}-{day}.done"


def read_lines(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.readlines()
    except FileNotFoundError:
        return []


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def scrape(store, day, sections_per_run=SECTIONS_PER_RUN):
    """Fetch the next sections not done yet; failed ones are retried by
    the next run. Returns False if any section failed."""
    module = importlib.import_module(store)
    csv_path, done_path = paths(store, day)
    done = [line.strip() for line in read_lines(done_path)]
    todo = [s for s in module.SECTIONS if s not in done][:sections_per_run]
    rows, failed = [], []

    for section in todo:
        try:
            this = net.paginate(lambda page: module.fetch_page(section, page), workers=1)
        except Exception as e:
            print(f"[{store}] {section}: error {e!r}")
            failed.append(section)

            continue

        print(f"[{store}] {section}: {len(this)} items")
        rows += this
        done.append(section)

    os.makedirs("pending", exist_ok=True)
    write_lines(csv_path, sm.sort_lines(read_lines(csv_path) + sm.csv_lines(rows, day)))
    write_lines(done_path, [f"{s}\n" for s in done])
    print(f"[{store}] {day}: {len(done)}/{len(module.SECTIONS)} sections done")

    return not failed


def finalize(store, day):
    """Move the day's pending csv to smdata/ if it passes sm.validate().
    Returns False if it failed or sections are missing."""
    module = importlib.import_module(store)
    csv_path, done_path = paths(store, day)
    lines = read_lines(csv_path)
    done = {line.strip() for line in read_lines(done_path)}
    missing = [s for s in module.SECTIONS if s not in done]

    if missing:
        print(f"[{store}] {day}: missing sections: {', '.join(missing)}")

    sms = {store: lines}
    (rows, prev, ok), = sm.validate(sms, day).values()
    print(f"[{store}] {day}: {rows} rows, previous {prev}: {'ok' if ok else 'FAILED'}")

    if ok:
        os.makedirs("smdata", exist_ok=True)
        write_lines(f"smdata/{store}-{day}.csv", lines)

    for path in (csv_path, done_path):
        if os.path.exists(path):
            os.remove(path)

    return ok and not missing


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    s = commands.add_parser("scrape")
    s.add_argument("store")
    s.add_argument("--date", default=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"))
    s.add_argument("--sections", type=int, default=SECTIONS_PER_RUN)
    f = commands.add_parser("finalize")
    f.add_argument("store")
    f.add_argument("date")
    args = parser.parse_args()

    if args.command == "scrape":
        ok = scrape(args.store, args.date, args.sections)
    else:
        ok = finalize(args.store, args.date)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
