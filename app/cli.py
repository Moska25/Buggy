"""Command line for CI: run the benchmark, gate on recall, export the results.

    python -m app.cli bench --min-recall 0.9
    python -m app.cli bench --json out.json --junit out.xml
    python -m app.cli compare docs/bench-baseline.json out.json

`bench` exits non-zero when a selected suite scores below the threshold, which
is what makes it usable as a build step. `compare` exits non-zero when recall
regressed against a committed baseline, which is what makes the workflow in
.github/workflows/bench.yml meaningful rather than decorative.

Nothing here talks to the network and nothing needs an API key.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence
from xml.etree import ElementTree as ET

from . import runner
from .defects import DEFECTS
from .suites import BY_ID as SUITE_BY_ID
from .suites import SUITE_IDS

COLUMNS = ("suite", "checks", "found", "recall", "precision", "fp", "mean ttd", "runtime")


# --------------------------------------------------------------- rendering ---

def scorecard_rows(report: runner.RunReport) -> list[list[str]]:
    return [
        [
            s.suite,
            str(s.n_checks),
            f"{s.detected}/{s.n_defects}",
            f"{s.recall * 100:.1f}%",
            f"{s.precision:.2f}",
            str(s.fp_results),
            f"{s.mttd_ms:.2f} ms",
            f"{s.runtime_ms:.1f} ms",
        ]
        for s in report.scores
    ]


def render_table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Fixed-width table. No dependency earns its place for eight columns."""
    widths = [
        max(len(str(header[i])), *(len(row[i]) for row in rows)) if rows else len(header[i])
        for i in range(len(header))
    ]
    def join(cells):
        return "  ".join(c.ljust(w) for c, w in zip(cells, widths)).rstrip()

    return "\n".join([
        join(h.upper() for h in header),
        join("-" * w for w in widths),
        *(join(row) for row in rows),
    ])


# ----------------------------------------------------------------- exports ---

def to_dict(report: runner.RunReport) -> dict[str, Any]:
    """The run as JSON-safe data, shaped like `runner.load_run` reads back."""
    return {
        "run": {
            "seed": report.seed,
            "kind": report.kind,
            "label": report.label,
            "n_builds": report.n_builds,
            "n_checks": len({c for (_s, c, _b) in report.results}),
            "n_results": len(report.results),
            "duration_ms": report.duration_ms,
            "repeats": report.repeats,
        },
        "suite_ids": report.suite_ids,
        "defect_ids": report.defect_ids,
        "scores": [vars(s) for s in report.scores],
        # tuple keys are not JSON, so detections travel as records
        "detections": [
            {"suite": suite, "defect_id": defect, **info}
            for (suite, defect), info in sorted(report.detections.items())
        ],
    }


def from_json(path: str | Path) -> dict[str, Any]:
    """Read an exported run back into `runner.load_run`'s shape, tuple keys and all."""
    data = json.loads(Path(path).read_text())
    return {
        "run": data["run"],
        "scores": data["scores"],
        "suite_ids": data["suite_ids"],
        "defect_ids": data["defect_ids"],
        "detections": {
            (d["suite"], d["defect_id"]): d for d in data["detections"]
        },
    }


def to_junit(report: runner.RunReport) -> ET.ElementTree:
    """One JUnit `testsuite` per benchmark suite, one `testcase` per defect.

    A missed defect is the failure, not a failing check: in this inversion the
    thing under test is the suite. `<skipped>` never appears - every defect is
    always attempted.
    """
    root = ET.Element("testsuites", name="buggy", time=f"{report.duration_ms / 1000:.4f}")
    total_tests = total_failures = 0
    for score in report.scores:
        cases = []
        for defect_id in report.defect_ids:
            info = report.detections.get((score.suite, defect_id), {})
            case = ET.Element(
                "testcase",
                classname=f"buggy.{score.suite}",
                name=f"detects {defect_id}",
                time=f"{info.get('ms', 0.0) / 1000:.6f}",
            )
            if not info.get("detected"):
                ET.SubElement(
                    case,
                    "failure",
                    message=f"{score.suite} did not detect {defect_id}",
                    type="MissedDefect",
                ).text = f"No check in {score.suite} failed on the {defect_id} build while passing on clean."
            cases.append(case)
        failures = sum(1 for c in cases if c.find("failure") is not None)
        suite_el = ET.SubElement(
            root,
            "testsuite",
            name=score.suite,
            tests=str(len(cases)),
            failures=str(failures),
            errors="0",
            skipped="0",
            time=f"{score.runtime_ms / 1000:.4f}",
        )
        suite_el.extend(cases)
        total_tests += len(cases)
        total_failures += failures
    root.set("tests", str(total_tests))
    root.set("failures", str(total_failures))
    root.set("errors", "0")
    return ET.ElementTree(root)


# -------------------------------------------------------------- subcommands ---

def cmd_bench(args: argparse.Namespace, out) -> int:
    suite_ids = args.suite or list(SUITE_IDS)
    unknown = [s for s in suite_ids if s not in SUITE_BY_ID]
    if unknown:
        print(f"unknown suite(s): {', '.join(unknown)}", file=out)
        return 2

    report = (
        runner.run_and_save(suite_ids=suite_ids, seed=args.seed, kind="cli",
                            label=f"CLI bench: {len(suite_ids)} suites"
                                  if len(suite_ids) != 1 else "CLI bench: 1 suite")
        if args.save
        else runner.run(suite_ids=suite_ids, seed=args.seed)
    )

    print(render_table(COLUMNS, scorecard_rows(report)), file=out)
    print(
        f"\n{report.n_builds} builds, {len(report.results)} check results, "
        f"{report.duration_ms:.0f} ms, seed {report.seed}",
        file=out,
    )

    if args.json:
        Path(args.json).write_text(json.dumps(to_dict(report), indent=2, default=str))
        print(f"wrote {args.json}", file=out)
    if args.junit:
        to_junit(report).write(args.junit, encoding="unicode", xml_declaration=True)
        print(f"wrote {args.junit}", file=out)

    if args.min_recall is None:
        return 0
    below = [s for s in report.scores if s.recall < args.min_recall]
    for score in below:
        print(
            f"FAIL {score.suite}: recall {score.recall:.1%} is below the "
            f"{args.min_recall:.0%} threshold",
            file=out,
        )
    return 1 if below else 0


def cmd_compare(args: argparse.Namespace, out) -> int:
    """Recall delta against a committed baseline. Markdown, for a CI step summary."""
    base = {s["suite"]: s for s in from_json(args.baseline)["scores"]}
    head = {s["suite"]: s for s in from_json(args.current)["scores"]}

    rows, regressions = [], []
    for suite_id in sorted(set(base) | set(head)):
        before = base.get(suite_id, {}).get("recall")
        after = head.get(suite_id, {}).get("recall")
        if before is None or after is None:
            rows.append([suite_id, "n/a" if before is None else f"{before:.1%}",
                         "n/a" if after is None else f"{after:.1%}", "new or removed"])
            continue
        delta = after - before
        rows.append([suite_id, f"{before:.1%}", f"{after:.1%}", f"{delta:+.1%}"])
        if delta < -args.max_drop:
            regressions.append((suite_id, before, after))

    print("| suite | baseline | current | delta |", file=out)
    print("| --- | --- | --- | --- |", file=out)
    for row in rows:
        print("| " + " | ".join(row) + " |", file=out)

    for suite_id, before, after in regressions:
        print(f"\nREGRESSION {suite_id}: recall fell {before:.1%} -> {after:.1%}", file=out)
    return 1 if regressions else 0


def main(argv: Sequence[str] | None = None, out=None) -> int:
    out = out or sys.stdout
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    bench = sub.add_parser("bench", help="run the benchmark and print the scorecard")
    bench.add_argument("--suite", action="append", help="restrict to a suite (repeatable)")
    bench.add_argument("--seed", type=int, default=runner.DEFAULT_SEED)
    bench.add_argument("--min-recall", type=float, default=None,
                       help="exit 1 if any selected suite scores below this (0-1)")
    bench.add_argument("--json", help="write the run as JSON to this path")
    bench.add_argument("--junit", help="write JUnit XML to this path")
    bench.add_argument("--save", action="store_true", help="also persist the run to SQLite")
    bench.set_defaults(fn=cmd_bench)

    compare = sub.add_parser("compare", help="recall delta between two exported runs")
    compare.add_argument("baseline")
    compare.add_argument("current")
    compare.add_argument("--max-drop", type=float, default=0.0,
                         help="tolerated recall drop before it counts as a regression")
    compare.set_defaults(fn=cmd_compare)

    args = parser.parse_args(argv)
    return args.fn(args, out)


if __name__ == "__main__":
    sys.exit(main())
