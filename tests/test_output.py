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

    report = sm.validate(sms, "2026-10-20")

    assert report == {"empty": (0, 100, False), "short": (10, 100, False), "ok": (90, 100, True)}
    assert list(sms) == ["ok"]


def test_summary():
    import sm

    out = sm.summary({"a": (110, 100, True), "b": (0, None, False)}, {"a": 3.2, "b": 1})

    assert out.splitlines()[1].split() == ["a", "110", "100", "+10.0%", "3s", "ok"]
    assert out.splitlines()[2].split() == ["b", "0", "-", "-", "1s", "FAILED"]
