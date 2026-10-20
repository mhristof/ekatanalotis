import sys
import types

import pytest

import slow
import sm


@pytest.fixture
def store(tmp_path, monkeypatch):
    """A fake store with 3 sections of 2 products each, 1 page per section."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sm, "previous_count", lambda store, today: None)
    module = types.ModuleType("fakestore")
    module.SECTIONS = ["a", "b", "c"]
    module.fail = set()

    def fetch_page(section, page):
        if section in module.fail:
            raise ValueError("blocked")
        return [[f"{section}{i}", f"name,{section}", 1.5] for i in (1, 2)] if page == 1 else []

    module.fetch_page = fetch_page
    monkeypatch.setitem(sys.modules, "fakestore", module)

    return module


def test_scrape_accumulates_and_retries_failed(store, tmp_path):
    store.fail = {"a"}
    assert slow.scrape("fakestore", "2026-10-21", 2) is False
    assert (tmp_path / "pending/fakestore-2026-10-21.done").read_text() == "b\n"

    store.fail = set()
    assert slow.scrape("fakestore", "2026-10-21", 2) is True
    assert slow.scrape("fakestore", "2026-10-21", 2) is True

    assert (tmp_path / "pending/fakestore-2026-10-21.csv").read_text() == "".join(
        f"2026-10-21,{s}{i},name-{s},1.5\n" for s in "abc" for i in (1, 2)
    )


def test_finalize_moves_csv_to_smdata(store, tmp_path):
    for _ in range(2):
        slow.scrape("fakestore", "2026-10-21", 2)

    assert slow.finalize("fakestore", "2026-10-21") is True
    assert (tmp_path / "smdata/fakestore-2026-10-21.csv").read_text().count("\n") == 6
    assert not (tmp_path / "pending/fakestore-2026-10-21.csv").exists()


def test_finalize_partial_day_is_written_but_fails(store, tmp_path):
    slow.scrape("fakestore", "2026-10-21", 2)

    assert slow.finalize("fakestore", "2026-10-21") is False
    assert (tmp_path / "smdata/fakestore-2026-10-21.csv").read_text().count("\n") == 4


def test_finalize_empty_day_is_not_written(store, tmp_path):
    assert slow.finalize("fakestore", "2026-10-21") is False
    assert not (tmp_path / "smdata").exists()
