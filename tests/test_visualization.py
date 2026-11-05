import math

import pytest

from colorslot.coloring import dsatur_coloring
from colorslot.visualization import VisualizationError, circular_layout, plot_conflict_graph, slot_colors


def test_circular_layout_is_deterministic_and_on_unit_circle():
    vertices = ["A", "B", "C", "D"]
    layout = circular_layout(vertices)
    assert layout == circular_layout(vertices)
    for x, y in layout.values():
        assert math.hypot(x, y) == pytest.approx(1.0)
    assert layout["A"] == pytest.approx((0.0, 1.0))  # first vertex at the top
    assert len(set(layout.values())) == 4


def test_slot_colors_are_distinct_for_many_slots():
    colors = slot_colors(25)
    assert len(colors) == len(set(colors)) == 25
    assert all(c.startswith("#") and len(c) == 7 for c in colors)


def test_plot_writes_png(sample_graph, tmp_path):
    pytest.importorskip("matplotlib")
    target = tmp_path / "plots" / "network.png"
    path = plot_conflict_graph(sample_graph, dsatur_coloring(sample_graph), target)
    assert path == target
    assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_plot_rejects_empty_graph(tmp_path):
    pytest.importorskip("matplotlib")
    from colorslot.graph import ConflictGraph

    with pytest.raises(VisualizationError, match="empty"):
        plot_conflict_graph(ConflictGraph(), {}, tmp_path / "x.png")
