"""Catch-wheel geometry.

One spoke per defect, one ring per suite, rings running best-recall-first from
the centre out. Every arc is computed here so the templates only place strings:
the page renders identically with scripting off, and app.js only adds hover.
"""

from __future__ import annotations

import math

VIEWBOX = 560
C = VIEWBOX / 2

_OUTER = 232.0  # outer edge of the outermost ring
_BAND = 32.0  # radial thickness of one ring
_GAP = 6.0  # space between rings
_LABEL_R = 252.0  # where the spoke labels sit
_STAGGER_MS = 12  # per-cell animation delay


def ring_radii(n: int) -> list[tuple[float, float]]:
    """Inner/outer radius per ring, innermost first, for n suites."""
    span = n * _BAND + (n - 1) * _GAP
    r0 = _OUTER - span
    return [(r0 + i * (_BAND + _GAP), r0 + i * (_BAND + _GAP) + _BAND) for i in range(n)]


def arc_path(r0: float, r1: float, a0: float, a1: float) -> str:
    """An annular sector, in viewBox units."""
    def at(r: float, a: float) -> tuple[float, float]:
        return C + r * math.cos(a), C + r * math.sin(a)

    x0, y0 = at(r1, a0)
    x1, y1 = at(r1, a1)
    x2, y2 = at(r0, a1)
    x3, y3 = at(r0, a0)
    large = 1 if a1 - a0 > math.pi else 0
    return (
        f"M{x0:.2f} {y0:.2f} "
        f"A{r1:g} {r1:g} 0 {large} 1 {x1:.2f} {y1:.2f} "
        f"L{x2:.2f} {y2:.2f} "
        f"A{r0:g} {r0:g} 0 {large} 0 {x3:.2f} {y3:.2f} Z"
    )


def build(data: dict, defect_by_id: dict, suite_by_id: dict, link: bool = False) -> dict | None:
    """Everything the wheel template needs, from one stored run."""
    if not data or not data["scores"] or not data["defect_ids"]:
        return None

    ranked = [s["suite"] for s in data["scores"]]
    radii = ring_radii(len(ranked))
    defect_ids = data["defect_ids"]
    step = math.tau / len(defect_ids)
    gap = step * 0.1
    cells: list[dict] = []
    spokes: list[dict] = []

    for di, did in enumerate(defect_ids):
        defect = defect_by_id[did]
        a0 = -math.pi / 2 + di * step + gap / 2
        a1 = -math.pi / 2 + (di + 1) * step - gap / 2
        hits = 0

        for ri, sid in enumerate(ranked):
            # sqlite3.Row, so index rather than .get
            info = data["detections"].get((sid, did))
            hit = bool(info["detected"]) if info else False
            hits += hit
            name = suite_by_id[sid].name
            cells.append({
                "defect_id": did,
                "hit": hit,
                "d": arc_path(radii[ri][0], radii[ri][1], a0, a1),
                "delay_ms": (di * len(ranked) + ri) * _STAGGER_MS,
                "tip": (
                    f"{name} caught {did} via {info['first_check_id']}"
                    if hit else f"{name} missed {did}: {defect.hint}"
                ),
                "href": f"/defects/{did}" if link else "",
            })

        caption = f"{defect.title} — caught by {hits} of {len(ranked)}"
        for cell in cells[-len(ranked):]:
            cell["caption"] = caption

        mid = -math.pi / 2 + (di + 0.5) * step
        spokes.append({
            "defect_id": did,
            "label": did,
            "left": f"{(C + _LABEL_R * math.cos(mid)) / VIEWBOX * 100:.2f}%",
            "top": f"{(C + _LABEL_R * math.sin(mid)) / VIEWBOX * 100:.2f}%",
        })

    return {
        "viewbox": VIEWBOX,
        "cells": cells,
        "spokes": spokes,
        "hub": f"{len(defect_ids)} × {len(ranked)}",
        "caption": "Hover a spoke to read its defect",
        "rings": [
            {
                "suite": s["suite"],
                "name": suite_by_id[s["suite"]].name,
                "recall": s["recall"],
            }
            for s in data["scores"]
        ],
    }
