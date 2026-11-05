"""Optional Matplotlib rendering of the colored conflict graph.

Matplotlib is imported lazily and rendered through the Agg canvas, so no
display is needed and the rest of ColorSlot works without Matplotlib.
"""

from __future__ import annotations

import colorsys
import math
from collections.abc import Mapping
from pathlib import Path

from .graph import ConflictGraph

_BASE_COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
]
_MAX_EDGE_LABELS = 25


class VisualizationError(RuntimeError):
    """Raised when the graph cannot be drawn."""


def circular_layout(vertices: list[str]) -> dict[str, tuple[float, float]]:
    """Place vertices evenly on the unit circle, first vertex at the top."""
    n = len(vertices)
    layout: dict[str, tuple[float, float]] = {}
    for index, vertex in enumerate(vertices):
        angle = math.pi / 2 - 2 * math.pi * index / n
        layout[vertex] = (math.cos(angle), math.sin(angle))
    return layout


def slot_colors(count: int) -> list[str]:
    """``count`` distinct hex colors; the first ten are a fixed readable palette."""
    colors = list(_BASE_COLORS[:count])
    extra = count - len(colors)
    for i in range(extra):
        hue = (i * 0.618033988749895) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 0.55, 0.85)
        colors.append("#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255)))
    return colors


def plot_conflict_graph(
    graph: ConflictGraph,
    coloring: Mapping[str, int],
    output_path: str | Path,
    title: str = "Course conflict graph",
) -> Path:
    """Save a PNG of the graph with vertices colored by exam slot."""
    try:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        from matplotlib.lines import Line2D
    except ImportError as exc:
        raise VisualizationError(
            "matplotlib is required for --plot (install it with: pip install matplotlib)"
        ) from exc

    vertices = graph.vertices()
    if not vertices:
        raise VisualizationError("cannot plot an empty graph")

    slots = sorted(set(coloring[v] for v in vertices))
    palette = dict(zip(slots, slot_colors(len(slots))))
    layout = circular_layout(vertices)
    max_weight = max((w for _, _, w in graph.edges()), default=1)

    side = min(14.0, max(7.0, 4.0 + 0.45 * len(vertices)))
    figure = Figure(figsize=(side, side * 0.85))
    FigureCanvasAgg(figure)
    ax = figure.add_subplot(1, 1, 1)

    label_edges = graph.num_edges <= _MAX_EDGE_LABELS
    for a, b, weight in graph.edges():
        (x1, y1), (x2, y2) = layout[a], layout[b]
        ax.plot([x1, x2], [y1, y2], color="#888888", alpha=0.55,
                linewidth=0.8 + 2.2 * weight / max_weight, zorder=1)
        if label_edges:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2, str(weight), fontsize=7, color="#444444",
                    ha="center", va="center", zorder=2,
                    bbox={"boxstyle": "round,pad=0.12", "fc": "white", "ec": "none", "alpha": 0.8})

    node_size = max(140.0, 1100.0 / math.sqrt(len(vertices)))
    for vertex in vertices:
        x, y = layout[vertex]
        ax.scatter([x], [y], s=node_size, color=palette[coloring[vertex]],
                   edgecolors="black", linewidths=0.8, zorder=3)
        ha = "center" if abs(x) < 0.15 else ("left" if x > 0 else "right")
        ax.text(x * 1.1, y * 1.1, vertex, fontsize=9, ha=ha, va="center", zorder=4)

    legend_handles = [
        Line2D([0], [0], marker="o", linestyle="", markersize=9, markerfacecolor=palette[s],
               markeredgecolor="black", label=f"Slot {s}")
        for s in slots
    ]
    ax.legend(handles=legend_handles, title="Exam slot", loc="upper left",
              bbox_to_anchor=(1.02, 1.0), frameon=False)
    ax.set_title(f"{title} ({len(slots)} slots)")
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.35, 1.35)
    ax.set_aspect("equal")
    ax.axis("off")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=150, bbox_inches="tight")
    return path
