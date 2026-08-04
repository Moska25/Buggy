"""Idempotent, deterministic seed.

Executes one full benchmark run - every suite against every seeded defect - and
stores it, so every page has real content on first load. Running it twice does
nothing the second time, and the fixed seed means the stored run is identical on
every machine.
"""

from __future__ import annotations

from . import db, runner


def main() -> None:
    db.bootstrap()
    with db.connect() as con:
        existing = db.one(con, "SELECT COUNT(*) AS n FROM runs WHERE kind = 'benchmark'")
    if existing and existing["n"]:
        print(f"seed: {existing['n']} benchmark run(s) already stored, nothing to do")
        return

    report = runner.run_and_save(kind="benchmark", label="Full benchmark: all suites, all defects")
    best = report.scores[0]
    worst = report.scores[-1]
    print(
        f"seed: run #{report.run_id} stored - {report.n_builds} builds, "
        f"{len(report.results)} check results in {report.duration_ms:.0f} ms"
    )
    print(f"seed: best recall {best.suite} {best.recall:.1%}, worst {worst.suite} {worst.recall:.1%}")


if __name__ == "__main__":
    main()
