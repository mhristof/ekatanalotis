"""The CSV files are the product of this repo; make sure the on-disk
format does not change."""

from sm import save_to_file


def test_save_to_file_format(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    save_to_file(
        {"store": [["1", "a,b", 1.5], ["2", "c", "0.50"]]},
        "2026-10-20",
    )

    assert (tmp_path / "smdata" / "store-2026-10-20.csv").read_text() == (
        "2026-10-20,1,a-b,1.5\n" "2026-10-20,2,c,0.50\n"
    )
