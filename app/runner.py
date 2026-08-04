"""The benchmark runner.

One run does this:

  1. Build the matrix. One build per seeded defect, with exactly that defect
     active and nothing else, plus one clean build with none active.
  2. Execute every check of every selected suite against every build, capturing
     pass/fail, a detail string, a duration, and the ordered step log.
  3. Attribute the results.

THE DETECTION RULE - this is the whole point of the project:

    detected(defect, check) = check FAILED on that defect's build
                          AND check PASSED on the clean build

A check that fails on the clean build has not found anything. It is a false
positive, and it is barred from earning detection credit for any defect, no
matter how many defective builds it also fails on. That guard is enforced in
`_score`, not merely documented: without it a suite could top the table by
asserting nonsense, which is exactly the failure mode this benchmark exists to
expose.

Determinism: the only nondeterministic defect reads from a seeded generator
that the runner reseeds before every check execution, keyed on
(run seed, build, repeat, check id) via crc32 - never Python's salted hash. The
same seed therefore reproduces a run exactly, while repeats of the same build
genuinely differ, which is what makes the flake rate a measurement.
"""

from __future__ import annotations

import json
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from . import db
from .defects import DEFECTS, NONDETERMINISTIC_ID
from .suites import BY_ID as SUITE_BY_ID
from .suites import SUITE_IDS, Check, CheckFailed, Ctx, all_checks
from .targets import rng

#: Build key for the variant with no defect active.
CLEAN = "clean"

DEFAULT_SEED = 20260804
DEFAULT_REPEATS = 5


@dataclass
class Result:
    suite: str
    check_id: str
    build: str
    passed: bool
    detail: str
    duration_us: float
    steps: list[dict[str, str]]


@dataclass
class Score:
    suite: str
    n_checks: int
    detected: int
    n_defects: int
    recall: float
    precision: float
    fp_checks: int
    fp_results: int
    mttd_ms: float
    runtime_ms: float
    flake_rate: float
    flake_checks: int
    nd_hits: int
    nd_repeats: int


@dataclass
class RunReport:
    seed: int
    kind: str
    label: str
    suite_ids: list[str]
    defect_ids: list[str]
    repeats: int
    duration_ms: float
    results: dict[tuple[str, str, str], Result]
    scores: list[Score]
    detections: dict[tuple[str, str], dict]
    fp_checks: dict[str, list[str]] = field(default_factory=dict)
    run_id: int | None = None

    @property
    def n_builds(self) -> int:
        return len(self.defect_ids) + 1


# --------------------------------------------------------------- execution ---

def _seed_for(seed: int, build: str, repeat: int, check_id: str) -> int:
    """Deterministic per-execution seed. crc32, never hash() - hash() is salted."""
    return zlib.crc32(f"{seed}|{build}|{repeat}|{check_id}".encode()) & 0xFFFFFFFF


def execute_check(chk: Check, active: set[str], seed: int, build: str, repeat: int) -> Result:
    """Run one check against one build. Never raises."""
    rng.reseed(_seed_for(seed, build, repeat, chk.id))
    ctx = Ctx(active=set(active))
    started = time.perf_counter_ns()
    try:
        chk.fn(ctx)
        passed, detail = True, "all assertions held"
    except CheckFailed as exc:
        passed, detail = False, str(exc)
    except Exception as exc:  # a target blowing up is a failing check, not a crashed run
        passed, detail = False, f"{type(exc).__name__}: {exc}"
        ctx.steps.append({"kind": "fail", "text": f"unexpected {type(exc).__name__}: {exc}"})
    duration_us = (time.perf_counter_ns() - started) / 1000.0
    return Result(chk.suite, chk.id, build, passed, detail, duration_us, ctx.steps)


def run(
    defect_ids: Iterable[str] | None = None,
    suite_ids: Iterable[str] | None = None,
    seed: int = DEFAULT_SEED,
    repeats: int = DEFAULT_REPEATS,
    kind: str = "benchmark",
    label: str = "",
) -> RunReport:
    defect_ids = list(defect_ids) if defect_ids is not None else [d.id for d in DEFECTS]
    suite_ids = list(suite_ids) if suite_ids is not None else list(SUITE_IDS)
    checks = all_checks(suite_ids)
    started = time.perf_counter_ns()

    results: dict[tuple[str, str, str], Result] = {}
    for build in [CLEAN, *defect_ids]:
        active = set() if build == CLEAN else {build}
        for chk in checks:
            results[(chk.suite, chk.id, build)] = execute_check(chk, active, seed, build, 0)

    # Repeat the nondeterministic build to measure outcome instability. Repeat 0
    # is the run already in `results`, so the matrix cell and the flake series
    # always agree with each other.
    outcomes: dict[tuple[str, str], list[bool]] = {}
    nd = NONDETERMINISTIC_ID if NONDETERMINISTIC_ID in defect_ids else None
    if nd and repeats > 0:
        for chk in checks:
            outcomes[(chk.suite, chk.id)] = [results[(chk.suite, chk.id, nd)].passed]
        for repeat in range(1, repeats):
            for chk in checks:
                extra = execute_check(chk, {nd}, seed, nd, repeat)
                outcomes[(chk.suite, chk.id)].append(extra.passed)

    duration_ms = (time.perf_counter_ns() - started) / 1_000_000.0
    scores, detections, fp_checks = _score(results, outcomes, defect_ids, suite_ids, repeats if nd else 0)

    return RunReport(
        seed=seed,
        kind=kind,
        label=label,
        suite_ids=suite_ids,
        defect_ids=defect_ids,
        repeats=repeats if nd else 0,
        duration_ms=duration_ms,
        results=results,
        scores=scores,
        detections=detections,
        fp_checks=fp_checks,
    )


# ----------------------------------------------------------------- scoring ---

def _score(
    results: dict[tuple[str, str, str], Result],
    outcomes: dict[tuple[str, str], list[bool]],
    defect_ids: list[str],
    suite_ids: list[str],
    repeats: int,
) -> tuple[list[Score], dict[tuple[str, str], dict], dict[str, list[str]]]:
    scores: list[Score] = []
    detections: dict[tuple[str, str], dict] = {}
    fp_checks: dict[str, list[str]] = {}

    for suite_id in suite_ids:
        checks = SUITE_BY_ID[suite_id].checks

        # A check that fails with no defect present is a false positive. It is
        # excluded from detection credit entirely - see the module docstring.
        clean_pass = {c.id: results[(suite_id, c.id, CLEAN)].passed for c in checks}
        fps = [c.id for c in checks if not clean_pass[c.id]]
        fp_checks[suite_id] = fps

        detected = 0
        ttds: list[float] = []
        for defect_id in defect_ids:
            detecting = [
                c.id
                for c in checks
                if clean_pass[c.id] and not results[(suite_id, c.id, defect_id)].passed
            ]
            first, elapsed_ms = "", 0.0
            if detecting:
                detected += 1
                # Time to detect: run the suite in registration order and stop at
                # the first check that detects. This is cumulative cost to signal,
                # not the cost of the detecting check alone.
                acc = 0.0
                for c in checks:
                    acc += results[(suite_id, c.id, defect_id)].duration_us
                    if c.id == detecting[0]:
                        break
                first, elapsed_ms = detecting[0], acc / 1000.0
                ttds.append(elapsed_ms)
            detections[(suite_id, defect_id)] = {
                "detected": bool(detecting),
                "first_check_id": first,
                "ms": elapsed_ms,
                "n_detecting": len(detecting),
                "checks": detecting,
            }

        suite_results = [r for (s, _cid, _b), r in results.items() if s == suite_id]
        failures = [r for r in suite_results if not r.passed]
        true_failures = [r for r in failures if r.build != CLEAN and clean_pass[r.check_id]]
        precision = (len(true_failures) / len(failures)) if failures else 0.0

        unstable = [key for key, series in outcomes.items() if key[0] == suite_id and len(set(series)) > 1]
        n_series = sum(1 for key in outcomes if key[0] == suite_id)
        flake_rate = (len(unstable) / n_series) if n_series else 0.0

        nd_hits = 0
        if repeats and NONDETERMINISTIC_ID in defect_ids:
            # How many of the repeats produced at least one true detection of the
            # nondeterministic defect.
            for i in range(repeats):
                if any(
                    clean_pass[c.id] and not outcomes[(suite_id, c.id)][i]
                    for c in checks
                    if (suite_id, c.id) in outcomes
                ):
                    nd_hits += 1

        scores.append(
            Score(
                suite=suite_id,
                n_checks=len(checks),
                detected=detected,
                n_defects=len(defect_ids),
                recall=detected / len(defect_ids) if defect_ids else 0.0,
                precision=precision,
                fp_checks=len(fps),
                fp_results=len(failures) - len(true_failures),
                mttd_ms=(sum(ttds) / len(ttds)) if ttds else 0.0,
                runtime_ms=sum(r.duration_us for r in suite_results) / 1000.0,
                flake_rate=flake_rate,
                flake_checks=len(unstable),
                nd_hits=nd_hits,
                nd_repeats=repeats,
            )
        )

    scores.sort(key=lambda s: (-s.recall, -s.precision))
    return scores, detections, fp_checks


# ------------------------------------------------------------- persistence ---

def save(report: RunReport, path=None) -> int:
    db.bootstrap(path)
    with db.connect(path) as con:
        cur = con.execute(
            "INSERT INTO runs (created_at, kind, label, seed, suites, defects, n_builds,"
            " n_checks, n_results, repeats, duration_ms)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                report.kind,
                report.label,
                report.seed,
                ",".join(report.suite_ids),
                ",".join(report.defect_ids),
                report.n_builds,
                len({(r.suite, r.check_id) for r in report.results.values()}),
                len(report.results),
                report.repeats,
                report.duration_ms,
            ),
        )
        run_id = int(cur.lastrowid)

        con.executemany(
            "INSERT INTO results (run_id, suite, check_id, build, passed, detail, duration_us, steps)"
            " VALUES (?,?,?,?,?,?,?,?)",
            [
                (run_id, r.suite, r.check_id, r.build, int(r.passed), r.detail,
                 r.duration_us, json.dumps(r.steps))
                for r in report.results.values()
            ],
        )
        con.executemany(
            "INSERT INTO scores (run_id, suite, n_checks, detected, n_defects, recall, precision,"
            " fp_checks, fp_results, mttd_ms, runtime_ms, flake_rate, flake_checks, nd_hits, nd_repeats)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (run_id, s.suite, s.n_checks, s.detected, s.n_defects, s.recall, s.precision,
                 s.fp_checks, s.fp_results, s.mttd_ms, s.runtime_ms, s.flake_rate,
                 s.flake_checks, s.nd_hits, s.nd_repeats)
                for s in report.scores
            ],
        )
        con.executemany(
            "INSERT INTO detections (run_id, suite, defect_id, detected, first_check_id, ms, n_detecting)"
            " VALUES (?,?,?,?,?,?,?)",
            [
                (run_id, suite, defect, int(info["detected"]), info["first_check_id"],
                 info["ms"], info["n_detecting"])
                for (suite, defect), info in report.detections.items()
            ],
        )
    report.run_id = run_id
    return run_id


def run_and_save(**kwargs) -> RunReport:
    report = run(**kwargs)
    save(report)
    return report


# ------------------------------------------------------------------ replay ---

def latest_run_id(kind: str = "benchmark", path=None) -> int | None:
    with db.connect(path) as con:
        row = db.one(con, "SELECT id FROM runs WHERE kind = ? ORDER BY id DESC LIMIT 1", (kind,))
    return int(row["id"]) if row else None


def list_runs(limit: int = 50, path=None) -> list:
    with db.connect(path) as con:
        return db.rows(
            con,
            "SELECT r.*, (SELECT MAX(recall) FROM scores s WHERE s.run_id = r.id) AS best_recall,"
            " (SELECT MIN(recall) FROM scores s WHERE s.run_id = r.id) AS worst_recall"
            " FROM runs r ORDER BY r.id DESC LIMIT ?",
            (limit,),
        )


def load_run(run_id: int, path=None) -> dict | None:
    """Read a stored run back for replay: header, scorecards, detection matrix."""
    with db.connect(path) as con:
        run_row = db.one(con, "SELECT * FROM runs WHERE id = ?", (run_id,))
        if run_row is None:
            return None
        scores = db.rows(con, "SELECT * FROM scores WHERE run_id = ? ORDER BY recall DESC, precision DESC", (run_id,))
        det_rows = db.rows(con, "SELECT * FROM detections WHERE run_id = ?", (run_id,))
    return {
        "run": run_row,
        "scores": scores,
        "detections": {(r["suite"], r["defect_id"]): r for r in det_rows},
        "suite_ids": [s for s in run_row["suites"].split(",") if s],
        "defect_ids": [d for d in run_row["defects"].split(",") if d],
    }


def load_results(run_id: int, suite: str | None = None, build: str | None = None, path=None) -> list:
    sql = "SELECT * FROM results WHERE run_id = ?"
    args: list = [run_id]
    if suite:
        sql += " AND suite = ?"
        args.append(suite)
    if build:
        sql += " AND build = ?"
        args.append(build)
    sql += " ORDER BY rowid"
    with db.connect(path) as con:
        return db.rows(con, sql, args)


def detecting_checks(run_id: int, defect_id: str, path=None) -> list:
    with db.connect(path) as con:
        return db.rows(
            con,
            "SELECT * FROM detections WHERE run_id = ? AND defect_id = ? ORDER BY suite",
            (run_id, defect_id),
        )


def fingerprint(report: RunReport) -> str:
    """Stable digest of a run's outcomes - used by the determinism test."""
    import hashlib

    payload = "|".join(
        f"{s}:{c}:{b}:{int(r.passed)}"
        for (s, c, b), r in sorted(report.results.items())
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
