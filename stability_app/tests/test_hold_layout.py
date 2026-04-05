"""Геометрия трюма и оценка высоты слоя угля."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hold_layout import (
    HOLD_LCG_AP_AFT_M,
    HOLD_LCG_AP_FWD_M,
    NUM_HOLD_SECTIONS,
    coal_uniform_layer_height_m,
    hold_length_m,
    section_centers_from_ap_m,
    section_edges_from_ap_m,
    section_length_m,
)


def test_section_edges_count_and_span():
    e = section_edges_from_ap_m()
    assert len(e) == NUM_HOLD_SECTIONS + 1
    assert e[0] == HOLD_LCG_AP_AFT_M
    assert e[-1] == HOLD_LCG_AP_FWD_M
    assert abs(sum(section_length_m() for _ in range(NUM_HOLD_SECTIONS)) - hold_length_m()) < 1e-6


def test_centers_between_edges():
    edges = section_edges_from_ap_m()
    centers = section_centers_from_ap_m()
    assert len(centers) == NUM_HOLD_SECTIONS
    for i, xc in enumerate(centers):
        assert edges[i] < xc < edges[i + 1]


def test_coal_6500_uniform():
    h, t_sec, vol = coal_uniform_layer_height_m(6500.0, 0.85)
    assert abs(t_sec - 325.0) < 1e-6
    assert vol > 0
    from hold_layout import BEAM_M

    assert abs(h * hold_length_m() * BEAM_M - vol) < 1e-3
