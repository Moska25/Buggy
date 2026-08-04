"""Runner tests: the detection rule, the scoring maths, and determinism.

The detection rule is the load-bearing part of this project, so it is tested
with a synthetic suite whose checks have known behaviour rather than only
against the shipped suites.
"""

import pytest

from app import runner, suites
from app.defects import DEFECTS, NONDETERMINISTIC_ID
from app.suites import Check, Ctx, Provenance, Suite


def _check(check_id, fn, suite="_probe"):
    return Check(id=check_id, suite=suite, target="checkout", title=check_id, intent="test", fn=fn)


@pytest.fixture
def probe_suite(monkeypatch):
    """Register a throwaway suite with checks whose behaviour we control."""

    def always_pass(ctx: Ctx) -> None:
        ctx.expect(True, "always true")

    def always_fail(ctx: Ctx) -> None:
        ctx.expect(False, "always false - a false positive")

    def fails_only_on_chk_002(ctx: Ctx) -> None:
        ctx.step("probe the tier boundary")
        ctx.expect("CHK-002" not in ctx.active, "tier boundary")

    def fails_only_on_chk_004(ctx: Ctx) -> None:
        ctx.expect("CHK-004" not in ctx.active, "shipping threshold")

    checks = [
        _check("P-PASS", always_pass),
        _check("P-FAIL", always_fail),
        _check("P-CHK002", fails_only_on_chk_002),
        _check("P-CHK004", fails_only_on_chk_004),
    ]
    prov = Provenance(author_kind="human", produced_on="2026-08-04", method="test fixture",
                      spec_access=True, code_access=True, tool_access=True,
                      recorded_fixture=False, caveat="test only")
    monkeypatch.setitem(suites.REGISTRY, "_probe", checks)
    monkeypatch.setitem(
        suites.BY_ID, "_probe",
        Suite(id="_probe", name="Probe", blurb="", expectation="", provenance=prov),
    )
    return "_probe"


def test_a_check_that_fails_on_clean_earns_no_detections(probe_suite):
    report = runner.run(defect_ids=["CHK-002", "CHK-004"], suite_ids=[probe_suite], repeats=0)
    score = report.scores[0]

    # P-FAIL fails on every build including clean. It must be a false positive
    # and must not be credited with detecting anything.
    assert score.fp_checks == 1
    assert report.fp_checks[probe_suite] == ["P-FAIL"]
    for defect_id in ("CHK-002", "CHK-004"):
        assert "P-FAIL" not in report.detections[(probe_suite, defect_id)]["checks"]


def test_detection_requires_failing_on_the_defect_build(probe_suite):
    report = runner.run(defect_ids=["CHK-002", "CHK-004"], suite_ids=[probe_suite], repeats=0)
    assert report.detections[(probe_suite, "CHK-002")]["checks"] == ["P-CHK002"]
    assert report.detections[(probe_suite, "CHK-004")]["checks"] == ["P-CHK004"]
    assert report.detections[(probe_suite, "CHK-002")]["detected"] is True


def test_recall_is_detected_over_total(probe_suite):
    # three defects, only two of which the probe suite can see
    report = runner.run(defect_ids=["CHK-002", "CHK-004", "CHK-005"], suite_ids=[probe_suite], repeats=0)
    score = report.scores[0]
    assert score.detected == 2
    assert score.n_defects == 3
    assert score.recall == pytest.approx(2 / 3)
    assert report.detections[(probe_suite, "CHK-005")]["detected"] is False


def test_precision_counts_only_true_detections_among_failures(probe_suite):
    report = runner.run(defect_ids=["CHK-002", "CHK-004"], suite_ids=[probe_suite], repeats=0)
    score = report.scores[0]
    # P-FAIL fails on all 3 builds (clean + 2 defects) = 3 failures, all bogus.
    # P-CHK002 and P-CHK004 each fail once, on their own build = 2 true detections.
    assert score.fp_results == 3
    assert score.precision == pytest.approx(2 / 5)


def test_clean_build_is_included_and_carries_no_defects(probe_suite):
    report = runner.run(defect_ids=["CHK-002"], suite_ids=[probe_suite], repeats=0)
    assert report.n_builds == 2
    assert report.results[(probe_suite, "P-CHK002", runner.CLEAN)].passed is True
    assert report.results[(probe_suite, "P-CHK002", "CHK-002")].passed is False


def test_builds_are_isolated_from_each_other(probe_suite):
    report = runner.run(defect_ids=["CHK-002", "CHK-004"], suite_ids=[probe_suite], repeats=0)
    # the CHK-002 probe must pass on the CHK-004 build and vice versa
    assert report.results[(probe_suite, "P-CHK002", "CHK-004")].passed is True
    assert report.results[(probe_suite, "P-CHK004", "CHK-002")].passed is True


def test_step_log_is_captured_in_order(probe_suite):
    report = runner.run(defect_ids=["CHK-002"], suite_ids=[probe_suite], repeats=0)
    steps = report.results[(probe_suite, "P-CHK002", "CHK-002")].steps
    assert [s["kind"] for s in steps] == ["step", "fail"]
    assert steps[0]["text"] == "probe the tier boundary"


def test_a_check_raising_an_unexpected_exception_fails_without_killing_the_run(monkeypatch):
    def explodes(ctx: Ctx) -> None:
        raise RuntimeError("boom")

    prov = Provenance(author_kind="human", produced_on="2026-08-04", method="test fixture",
                      spec_access=True, code_access=True, tool_access=True,
                      recorded_fixture=False, caveat="test only")
    monkeypatch.setitem(suites.REGISTRY, "_boom", [_check("P-BOOM", explodes, suite="_boom")])
    monkeypatch.setitem(suites.BY_ID, "_boom",
                        Suite(id="_boom", name="Boom", blurb="", expectation="", provenance=prov))
    report = runner.run(defect_ids=["CHK-002"], suite_ids=["_boom"], repeats=0)
    result = report.results[("_boom", "P-BOOM", runner.CLEAN)]
    assert result.passed is False
    assert "RuntimeError: boom" in result.detail


# ------------------------------------------------------------ full benchmark ---

@pytest.fixture(scope="module")
def full():
    return runner.run()


def test_full_run_covers_every_defect_and_suite(full):
    assert full.n_builds == len(DEFECTS) + 1
    assert len(full.results) == full.n_builds * sum(s.n_checks for s in full.scores)
    assert {s.suite for s in full.scores} == set(suites.SUITE_IDS)


def test_expert_suite_scores_highest_recall(full):
    by_suite = {s.suite: s for s in full.scores}
    assert by_suite["expert"].recall > by_suite["llm_tooled"].recall
    assert by_suite["llm_tooled"].recall > by_suite["llm_naive"].recall
    assert by_suite["llm_naive"].recall > by_suite["checklist"].recall


def test_the_naive_suite_is_the_only_one_with_false_positives(full):
    by_suite = {s.suite: s for s in full.scores}
    assert by_suite["llm_naive"].fp_checks == 2
    assert by_suite["llm_naive"].precision < 0.5
    for other in ("expert", "checklist", "llm_tooled"):
        assert by_suite[other].fp_checks == 0
        assert by_suite[other].precision == 1.0


def test_false_positive_checks_never_appear_as_detectors(full):
    for suite_id, ids in full.fp_checks.items():
        for defect in full.defect_ids:
            detectors = full.detections[(suite_id, defect)]["checks"]
            assert not set(ids) & set(detectors)


def test_tooled_suite_misses_something_the_expert_suite_catches(full):
    expert = {d for d in full.defect_ids if full.detections[("expert", d)]["detected"]}
    tooled = {d for d in full.defect_ids if full.detections[("llm_tooled", d)]["detected"]}
    assert expert - tooled, "the tooled fixture is supposed to have a blind spot"


def test_flake_is_measured_on_the_nondeterministic_build(full):
    by_suite = {s.suite: s for s in full.scores}
    assert all(s.nd_repeats == runner.DEFAULT_REPEATS for s in full.scores)
    # at least one suite must show genuine outcome instability, otherwise the
    # flake column is decorative rather than measured
    assert any(0 < s.flake_rate < 1 for s in full.scores)
    assert by_suite["llm_tooled"].flake_rate > 0


def test_only_the_nondeterministic_defect_causes_instability():
    stable = runner.run(defect_ids=[d.id for d in DEFECTS if d.id != NONDETERMINISTIC_ID], repeats=0)
    again = runner.run(defect_ids=[d.id for d in DEFECTS if d.id != NONDETERMINISTIC_ID], repeats=0)
    assert runner.fingerprint(stable) == runner.fingerprint(again)
    assert all(s.flake_rate == 0 for s in stable.scores)


def test_a_seeded_run_is_reproducible():
    a = runner.run(seed=4242)
    b = runner.run(seed=4242)
    assert runner.fingerprint(a) == runner.fingerprint(b)
    assert [s.recall for s in a.scores] == [s.recall for s in b.scores]


def test_time_to_detect_is_recorded_for_every_detection(full):
    for (suite_id, defect_id), info in full.detections.items():
        if info["detected"]:
            assert info["first_check_id"], (suite_id, defect_id)
            assert info["ms"] > 0


# ------------------------------------------------------------------ storage ---

def test_a_run_round_trips_through_sqlite(tmp_path):
    path = tmp_path / "t.db"
    report = runner.run(defect_ids=["CHK-002", "AUT-001"], suite_ids=["expert"], repeats=0)
    run_id = runner.save(report, path=path)

    loaded = runner.load_run(run_id, path=path)
    assert loaded["run"]["seed"] == report.seed
    assert loaded["defect_ids"] == ["CHK-002", "AUT-001"]
    assert loaded["detections"][("expert", "CHK-002")]["detected"] == 1

    results = runner.load_results(run_id, suite="expert", build=runner.CLEAN, path=path)
    assert len(results) == len(suites.BY_ID["expert"].checks)
    assert all(r["passed"] == 1 for r in results)


def test_stored_steps_survive_the_round_trip(tmp_path):
    from app import db

    path = tmp_path / "t.db"
    report = runner.run(defect_ids=["CHK-004"], suite_ids=["expert"], repeats=0)
    run_id = runner.save(report, path=path)
    rows = runner.load_results(run_id, suite="expert", build="CHK-004", path=path)
    failing = [r for r in rows if not r["passed"]]
    assert failing
    steps = db.loads(failing[0]["steps"])
    assert steps and any(s["kind"] == "fail" for s in steps)
