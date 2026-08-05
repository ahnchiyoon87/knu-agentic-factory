"""AMR 이동 경로 그래프.

config/layout.json 의 nodes/edges 로 만든 무방향 가중 그래프에서
다익스트라로 최단 경로를 구한다. 노드 수가 13개뿐이라 단순 구현으로 충분하다.
"""

from __future__ import annotations

import heapq
import math


class PathGraph:
    def __init__(self, layout: dict) -> None:
        self.nodes: dict[str, tuple[float, float]] = {
            name: (float(n["x"]), float(n["y"])) for name, n in layout["nodes"].items()
        }
        self.labels: dict[str, str] = {
            name: n.get("label", name) for name, n in layout["nodes"].items()
        }
        self.adj: dict[str, list[tuple[str, float]]] = {n: [] for n in self.nodes}
        for a, b in layout["edges"]:
            w = self._dist(self.nodes[a], self.nodes[b])
            self.adj[a].append((b, w))
            self.adj[b].append((a, w))

    @staticmethod
    def _dist(p: tuple[float, float], q: tuple[float, float]) -> float:
        return math.hypot(p[0] - q[0], p[1] - q[1])

    def nearest_node(self, x: float, y: float) -> str:
        return min(self.nodes, key=lambda n: self._dist(self.nodes[n], (x, y)))

    def shortest_path(self, start: str, goal: str) -> list[str]:
        """start → goal 노드 이름 목록. 도달 불가면 빈 목록."""
        if start == goal:
            return [goal]
        dist = {start: 0.0}
        prev: dict[str, str] = {}
        pq: list[tuple[float, str]] = [(0.0, start)]
        seen: set[str] = set()

        while pq:
            d, u = heapq.heappop(pq)
            if u in seen:
                continue
            seen.add(u)
            if u == goal:
                break
            for v, w in self.adj.get(u, ()):
                nd = d + w
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))

        if goal not in dist:
            return []

        path = [goal]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        return path

    def waypoints(self, from_x: float, from_y: float, goal: str) -> list[tuple[float, float]]:
        """현재 좌표에서 goal 노드까지의 경유 좌표 목록."""
        start = self.nearest_node(from_x, from_y)
        names = self.shortest_path(start, goal)
        if not names:
            return []
        return [self.nodes[n] for n in names]
