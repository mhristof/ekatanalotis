import net


def test_paginate_stops_at_first_empty_page():
    pages = {1: [["a"]], 2: [["b"]], 3: [], 4: [["never"]]}
    assert net.paginate(lambda page: pages[page]) == [["a"], ["b"]]


def test_paginate_max_pages():
    assert net.paginate(lambda page: [[page]], max_pages=2) == [[1], [2]]


def test_crawl_skips_failing_section():
    def fetch_page(section, page):
        if section == "bad":
            raise ValueError("boom")
        return [[section, page]] if page == 1 else []

    assert net.crawl("t", ["a", "bad", "b"], fetch_page) == [["a", 1], ["b", 1]]
