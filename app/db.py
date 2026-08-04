"""SQLite storage. Plain sqlite3, plain SQL strings, no ORM.

Four tables. `results` carries the ordered step log as a JSON column rather than
in a fifth table - one run writes a few thousand rows and the replay view reads
them back by run id, so a join would buy nothing.

`detections` and `scores` are derived from `results`, but they are persisted
anyway: it keeps the matrix and the scorecards to one query each, and it means
a stored run replays exactly as it was computed rather than being recomputed by
whatever the code does today.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path(__file__).resolve().parent.parent / "buggy.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at   TEXT    NOT NULL,
  kind         TEXT    NOT NULL,
  label        TEXT    NOT NULL DEFAULT '',
  seed         INTEGER NOT NULL,
  suites       TEXT    NOT NULL,
  defects      TEXT    NOT NULL,
  n_builds     INTEGER NOT NULL,
  n_checks     INTEGER NOT NULL,
  n_results    INTEGER NOT NULL,
  repeats      INTEGER NOT NULL,
  duration_ms  REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
  run_id      INTEGER NOT NULL,
  suite       TEXT    NOT NULL,
  check_id    TEXT    NOT NULL,
  build       TEXT    NOT NULL,
  passed      INTEGER NOT NULL,
  detail      TEXT    NOT NULL,
  duration_us REAL    NOT NULL,
  steps       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS scores (
  run_id      INTEGER NOT NULL,
  suite       TEXT    NOT NULL,
  n_checks    INTEGER NOT NULL,
  detected    INTEGER NOT NULL,
  n_defects   INTEGER NOT NULL,
  recall      REAL    NOT NULL,
  precision   REAL    NOT NULL,
  fp_checks   INTEGER NOT NULL,
  fp_results  INTEGER NOT NULL,
  mttd_ms     REAL    NOT NULL,
  runtime_ms  REAL    NOT NULL,
  flake_rate  REAL    NOT NULL,
  flake_checks INTEGER NOT NULL,
  nd_hits     INTEGER NOT NULL,
  nd_repeats  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS detections (
  run_id        INTEGER NOT NULL,
  suite         TEXT    NOT NULL,
  defect_id     TEXT    NOT NULL,
  detected      INTEGER NOT NULL,
  first_check_id TEXT   NOT NULL DEFAULT '',
  ms            REAL    NOT NULL DEFAULT 0,
  n_detecting   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_results_run   ON results(run_id, suite, build);
CREATE INDEX IF NOT EXISTS idx_scores_run    ON scores(run_id);
CREATE INDEX IF NOT EXISTS idx_detect_run    ON detections(run_id);
"""


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(str(path or DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def bootstrap(path: Path | str | None = None) -> None:
    with connect(path) as con:
        con.executescript(SCHEMA)


def rows(con: sqlite3.Connection, sql: str, args: Iterable[Any] = ()) -> list[sqlite3.Row]:
    return con.execute(sql, tuple(args)).fetchall()


def one(con: sqlite3.Connection, sql: str, args: Iterable[Any] = ()) -> sqlite3.Row | None:
    return con.execute(sql, tuple(args)).fetchone()


def loads(value: str) -> Any:
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return []
