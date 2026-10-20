"""The CSV files are the product of this repo; make sure the on-disk
format does not change."""

from sm import save_to_file


def test_save_to_file_format_sorted_deduped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    save_to_file(
        {"store": [["2", "c", "0.50"], ["1", "a,b", 1.5], ["2", "c", "0.50"]]},
        "2026-10-20",
    )

    assert (tmp_path / "smdata" / "store-2026-10-20.csv").read_text() == (
        "2026-10-20,1,a-b,1.5\n" "2026-10-20,2,c,0.50\n"
    )


def test_validate_drops_empty_and_short(monkeypatch):
    import sm

    monkeypatch.setattr(sm, "previous_count", lambda store, today: 100)
    sms = {"empty": [], "short": [["1", "a", 1]] * 10, "ok": [["1", "a", 1]] * 90}

    assert sm.validate(sms, "2026-10-20") == ["empty", "short"]
    assert list(sms) == ["ok"]
