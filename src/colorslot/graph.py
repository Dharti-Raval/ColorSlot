"""Undirected weighted conflict graph built from enrollment data."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import combinations

from .data_loader import EnrollmentData

Edge = tuple[str, str]


def edge_key(u: str, v: str) -> Edge:
    """Canonical (sorted) key for the undirected edge {u, v}."""
    return (u, v) if u < v else (v, u)


@dataclass
class ConflictGraph:
    """Adjacency-list graph: vertices are courses, edges are shared students.

    ``adjacency`` maps every vertex to the set of its neighbours (kept
    symmetric). ``weights`` maps each edge, stored once under its sorted key,
    to the number of distinct students enrolled in both courses.
    """

    adjacency: dict[str, set[str]] = field(default_factory=dict)
    weights: dict[Edge, int] = field(default_factory=dict)
    course_names: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_edges(
        cls, edges: Iterable[tuple[str, str]], vertices: Iterable[str] = ()
    ) -> "ConflictGraph":
        """Build a graph from an edge list, plus any extra isolated vertices."""
        graph = cls()
        for vertex in vertices:
            graph.add_vertex(vertex)
        for u, v in edges:
            graph.add_edge(u, v)
        return graph

    def add_vertex(self, course_id: str, course_name: str = "") -> None:
        self.adjacency.setdefault(course_id, set())
        if course_name:
            self.course_names[course_id] = course_name

    def add_edge(self, u: str, v: str, weight: int = 1) -> None:
        """Add (or reweight) the undirected edge {u, v}."""
        if u == v:
            raise ValueError(f"self-loops are not allowed: {u!r}")
        if weight < 1:
            raise ValueError("edge weight must be at least 1")
        self.add_vertex(u)
        self.add_vertex(v)
        self.adjacency[u].add(v)
        self.adjacency[v].add(u)
        self.weights[edge_key(u, v)] = weight

    def vertices(self) -> list[str]:
        return sorted(self.adjacency)

    def neighbors(self, vertex: str) -> set[str]:
        return self.adjacency[vertex]

    def has_edge(self, u: str, v: str) -> bool:
        return u in self.adjacency and v in self.adjacency[u]

    def weight(self, u: str, v: str) -> int:
        """Number of shared students, or 0 when the courses do not conflict."""
        return self.weights.get(edge_key(u, v), 0)

    def course_name(self, vertex: str) -> str:
        return self.course_names.get(vertex, "")

    def degree(self, vertex: str) -> int:
        return len(self.adjacency[vertex])

    def degrees(self) -> dict[str, int]:
        return {v: len(self.adjacency[v]) for v in self.vertices()}

    @property
    def num_vertices(self) -> int:
        return len(self.adjacency)

    @property
    def num_edges(self) -> int:
        return len(self.weights)

    def edges(self) -> list[tuple[str, str, int]]:
        """All edges as ``(course_a, course_b, shared_students)``, sorted."""
        return [(a, b, w) for (a, b), w in sorted(self.weights.items())]

    def density(self) -> float:
        """Edge count divided by the maximum possible, ``n(n-1)/2``."""
        n = self.num_vertices
        if n < 2:
            return 0.0
        return self.num_edges / (n * (n - 1) / 2)

    def connected_components(self) -> list[list[str]]:
        """Connected components, each sorted, ordered by their first vertex."""
        seen: set[str] = set()
        components: list[list[str]] = []
        for start in self.vertices():
            if start in seen:
                continue
            seen.add(start)
            stack = [start]
            component: list[str] = []
            while stack:
                vertex = stack.pop()
                component.append(vertex)
                for neighbor in self.adjacency[vertex]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
            components.append(sorted(component))
        return components


def build_conflict_graph(data: EnrollmentData) -> ConflictGraph:
    """Create the conflict graph for validated enrollment data.

    Every course becomes a vertex (even with no conflicts). For each student,
    every pair of their courses gains one shared student; because enrollments
    are stored as sets, a student is counted at most once per course pair.
    """
    graph = ConflictGraph()
    for course in sorted(data.course_students):
        graph.add_vertex(course, data.course_names.get(course, ""))

    courses_by_student: dict[str, set[str]] = {}
    for course, students in data.course_students.items():
        for student in students:
            courses_by_student.setdefault(student, set()).add(course)

    shared: dict[Edge, int] = {}
    for courses in courses_by_student.values():
        for pair in combinations(sorted(courses), 2):
            shared[pair] = shared.get(pair, 0) + 1

    for (a, b), count in sorted(shared.items()):
        graph.add_edge(a, b, count)
    return graph
