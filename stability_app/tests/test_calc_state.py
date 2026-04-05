"""Сериализация параметров расчёта."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calc_state import ALL_KEYS, APP_ID, apply_calc_state, export_calc_state


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
