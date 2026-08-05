"""CLI tests: the recall gate, the JSON round-trip, the JUnit contract, the diff."""

import io
import json
from xml.etree import ElementTree as ET

import pytest

from app import cli
from app.defects import DEFECTS
from app.suites import SUITE_IDS


def run_cli(*argv):
    out = io.StringIO()
    code = cli.main(list(argv), out=out)
    return code, out.getvalue()


# -------------------------------------------------------------- the gate ---

def test_bench_prints_a_row_per_suite_and_exits_zero_without_a_threshold():
    code, text = run_cli("bench")
    assert code == 0
    for suite_id in SUITE_IDS:
        assert suite_id in text
    assert "1296 check results" in text


def test_min_recall_fails_the_checklist_suite():
    code, text = run_cli("bench", "--suite", "checklist", "--min-recall", "0.9")
    assert code == 1
    assert "FAIL checklist" in text


def test_min_recall_passes_the_expert_suite():
    code, _ = run_cli("bench", "--suite", "expert", "--min-recall", "0.9")
    assert code == 0


def test_unknown_suite_is_rejected_without_running():
    code, text = run_cli("bench", "--suite", "nope")
    assert code == 2
    assert "unknown suite" in text


# ------------------------------------------------------------- the exports ---

def test_json_round_trips_into_load_run_shaped_data(tmp_path):
    path = tmp_path / "run.json"
    code, _ = run_cli("bench", "--json", str(path))
    assert code == 0

    restored = cli.from_json(path)
    assert set(restored) == {"run", "scores", "suite_ids", "defect_ids", "detections"}
    assert restored["defect_ids"] == [d.id for d in DEFECTS]
    assert restored["run"]["n_results"] == 1296
    # detections are keyed by (suite, defect) exactly as runner.load_run returns them
    key = (restored["suite_ids"][0], restored["defect_ids"][0])
    assert key in restored["detections"]
    assert {"detected", "first_check_id", "ms"} <= set(restored["detections"][key])
    # and the scores carry every field the web app reads
    assert {"suite", "recall", "precision", "fp_results", "mttd_ms"} <= set(restored["scores"][0])


def test_junit_xml_meets_the_junit_element_contract(tmp_path):
    """Structural contract, not schema validation.

    There is no single canonical JUnit XSD, and vendoring a third-party one to
    satisfy the word "schema" would break the offline rule for no gain. This
    asserts what consumers actually read: element nesting, the required
    attributes, and counts that agree with the cases present.
    """
    path = tmp_path / "junit.xml"
    code, _ = run_cli("bench", "--junit", str(path))
    assert code == 0

    root = ET.parse(path).getroot()
    assert root.tag == "testsuites"
    assert {"tests", "failures", "errors"} <= set(root.attrib)

    suites = root.findall("testsuite")
    assert len(suites) == len(SUITE_IDS)
    for suite in suites:
        assert {"name", "tests", "failures", "errors", "skipped", "time"} <= set(suite.attrib)
        cases = suite.findall("testcase")
        assert len(cases) == len(DEFECTS) == int(suite.get("tests"))
        assert int(suite.get("failures")) == sum(
            1 for c in cases if c.find("failure") is not None
        )
        for case in cases:
            assert {"classname", "name", "time"} <= set(case.attrib)
            for failure in case.findall("failure"):
                assert failure.get("message") and failure.text

    assert int(root.get("tests")) == sum(int(s.get("tests")) for s in suites)
    assert int(root.get("failures")) == sum(int(s.get("failures")) for s in suites)


def test_a_missed_defect_is_the_junit_failure(tmp_path):
    path = tmp_path / "junit.xml"
    run_cli("bench", "--junit", str(path))
    root = ET.parse(path).getroot()
    expert = next(s for s in root.findall("testsuite") if s.get("name") == "expert")
    failed = [c.get("name") for c in expert.findall("testcase") if c.find("failure") is not None]
    assert failed == ["detects CHK-003"]  # the one defect no suite catches


# -------------------------------------------------------------- the diff ---

def _write(path, scores):
    path.write_text(json.dumps({
        "run": {}, "suite_ids": [s["suite"] for s in scores], "defect_ids": [],
        "scores": scores, "detections": [],
    }))


def test_compare_is_quiet_when_recall_is_unchanged(tmp_path):
    base, head = tmp_path / "a.json", tmp_path / "b.json"
    _write(base, [{"suite": "expert", "recall": 0.94}])
    _write(head, [{"suite": "expert", "recall": 0.94}])
    code, text = run_cli("compare", str(base), str(head))
    assert code == 0
    assert "REGRESSION" not in text
    assert "+0.0%" in text


def test_compare_fails_on_a_recall_regression(tmp_path):
    base, head = tmp_path / "a.json", tmp_path / "b.json"
    _write(base, [{"suite": "expert", "recall": 0.94}])
    _write(head, [{"suite": "expert", "recall": 0.70}])
    code, text = run_cli("compare", str(base), str(head))
    assert code == 1
    assert "REGRESSION expert" in text


def test_compare_tolerates_a_drop_inside_the_allowance(tmp_path):
    base, head = tmp_path / "a.json", tmp_path / "b.json"
    _write(base, [{"suite": "expert", "recall": 0.94}])
    _write(head, [{"suite": "expert", "recall": 0.92}])
    code, _ = run_cli("compare", str(base), str(head), "--max-drop", "0.05")
    assert code == 0


def test_compare_reports_an_improvement_without_failing(tmp_path):
    base, head = tmp_path / "a.json", tmp_path / "b.json"
    _write(base, [{"suite": "expert", "recall": 0.70}])
    _write(head, [{"suite": "expert", "recall": 0.94}])
    code, text = run_cli("compare", str(base), str(head))
    assert code == 0
    assert "+24.0%" in text


def test_compare_marks_a_suite_that_only_exists_on_one_side(tmp_path):
    base, head = tmp_path / "a.json", tmp_path / "b.json"
    _write(base, [{"suite": "expert", "recall": 0.94}])
    _write(head, [{"suite": "expert", "recall": 0.94}, {"suite": "brand_new", "recall": 0.5}])
    code, text = run_cli("compare", str(base), str(head))
    assert code == 0
    assert "new or removed" in text


def test_cli_requires_a_subcommand():
    with pytest.raises(SystemExit):
        cli.main([])
