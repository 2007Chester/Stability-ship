"""Сериализация параметров расчёта."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

from calc_state import (
    ALL_KEYS,
    APP_ID,
    apply_calc_state,
    export_calc_state,
    save_local_calc_state,
    try_load_local_calc_state,
)


def test_export_apply_roundtrip():
    class FakeSS(dict):
        pass

    ss: FakeSS = FakeSS()
    for k in ALL_KEYS:
        if k == "preset_v2" or k == "last_preset_v2":
            ss[k] = "В грузу (из Excel)"
        elif k == "sb_x_from_midship":
            ss[k] = True
        else:
            ss[k] = 3.14

    out = export_calc_state(ss)
    assert out["app"] == "raid8-stability"
    assert "state" in out

    ss2: FakeSS = FakeSS()
    apply_calc_state(out, ss2)
    for k in ALL_KEYS:
        assert k in ss2
        if k in ("preset_v2", "last_preset_v2"):
            assert ss2[k] == ss[k]
        elif k == "sb_x_from_midship":
            assert ss2[k] is True
        else:
            assert abs(float(ss2[k]) - 3.14) < 1e-9


def test_wrong_app_raises():
    class FakeSS(dict):
        pass

    try:
        apply_calc_state({"app": "other", "version": 1, "state": {}}, FakeSS())
        assert False, "expected ValueError"
    except ValueError as e:
        assert APP_ID in str(e) or "приложения" in str(e).lower()


def test_local_file_save_load_roundtrip(tmp_path, monkeypatch):
    import calc_state

    fake = tmp_path / "saved_calc_state.json"
    monkeypatch.setattr(calc_state, "local_calc_state_path", lambda: fake)

    class FakeSS(dict):
        pass

    ss: FakeSS = FakeSS()
    for k in ALL_KEYS:
        if k in ("preset_v2", "last_preset_v2"):
            ss[k] = "В грузу (из Excel)"
        elif k == "sb_x_from_midship":
            ss[k] = True
        else:
            ss[k] = 2.0

    save_local_calc_state(ss)
    assert fake.is_file()
    data = json.loads(fake.read_text(encoding="utf-8"))
    assert data["app"] == APP_ID

    ss2: FakeSS = FakeSS()
    assert try_load_local_calc_state(ss2) is True
    assert ss2["sb_theta_flood"] == 2.0
    assert ss2["preset_v2"] == "В грузу (из Excel)"
