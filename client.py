#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""

"""

from click import clickhouse
import sys


def main():
    name = sys.argv[1]
    q = "select barcode, name from {table} where date == today() and positionCaseInsensitive(name, '{name}')"
    ch = clickhouse()

    print(f"searching for {name}")
    tables = ch.query("SHOW TABLES").result_rows

    for table in tables:
        table = table[0]
        try:
            result = ch.query(q.format(table=table, name=name)).result_rows
        except:
            continue

        for row in result:
            # csv with table name in front
            print(f"{table},{','.join(row)}")


if __name__ == "__main__":
    main()
