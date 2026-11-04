import pathlib
from export_demo import localize


def test_localize_copies_files_and_rewrites_paths(tmp_path):
    shots = tmp_path / "scans"; shots.mkdir()
    (shots / "a.png").write_bytes(b"x"); (shots / "b.png").write_bytes(b"y")
    out = tmp_path / "out"; out.mkdir()
    data = {"screenshot_path": str(shots / "a.png"),
            "findings": [{"crop_path": str(shots / "b.png"), "id": "x"}, {"crop_path": None}],
            "before_screenshot": str(shots / "missing.png")}
    res = localize(data, out)
    assert res["screenshot_path"] == "a.png" and res["findings"][0]["crop_path"] == "b.png"
    assert res["findings"][1]["crop_path"] is None and res["before_screenshot"] == "missing.png"
    assert (out / "a.png").exists() and (out / "b.png").exists() and not (out / "missing.png").exists()
