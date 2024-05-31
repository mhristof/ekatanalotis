#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""

"""
import clickhouse_connect  # pip install clickhouse-connect
from functools import cache


@cache
def clickhouse():
    try:
        return clickhouse_connect.get_client(
            host="localhost",
            port=8123,
            user="admin",
            password="admin",
            database="default",
        )
    except:
        return clickhouse_connect.get_client(
            host="clickhouse",
            port=8123,
            user="admin",
            password="admin",
            database="default",
        )
