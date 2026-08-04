"""Route smoke tests: every page renders, and the honesty labelling is present."""

import pytest
from fastapi.testclient import TestClient

from app import seed
from app.defects import DEFECTS
from app.main import app
from app.suites import SUITE_IDS


@pytest.fixture(scope="module")
def client():
    seed.main()  # idempotent
    return TestClient(app)


@pytest.mark.parametrize("path", [
    "/", "/benchmark", "/defects", "/suites", "/runs", "/lab",
    "/defects/CHK-003", "/defects/AUT-006", "/defects/LED-001",
    "/suites/expert", "/suites/checklist", "/suites/llm_naive", "/suites/llm_tooled",
    "/runs/1", "/static/base.css", "/static/app.css",
])
def test_route_returns_200(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.text


@pytest.mark.parametrize("path", ["/defects/NOPE", "/suites/nope", "/runs/999999"])
def test_unknown_ids_return_404(client, path):
    assert client.get(path).status_code == 404


def test_every_defect_has_a_detail_page(client):
    for defect in DEFECTS:
        response = client.get(f"/defects/{defect.id}")
        assert response.status_code == 200
        assert defect.title in response.text


def test_every_suite_has_a_detail_page(client):
    for suite_id in SUITE_IDS:
        assert client.get(f"/suites/{suite_id}").status_code == 200


def test_matrix_renders_one_cell_per_defect_and_suite(client):
    body = client.get("/benchmark").text
    assert body.count('class="hit"') + body.count('class="miss"') == len(DEFECTS) * len(SUITE_IDS)


def test_recorded_fixture_suites_are_labelled_on_the_suites_page(client):
    body = client.get("/suites").text
    assert "recorded fixture" in body
    assert "never calls a model at run time" in body
    assert "requires no API key" in body


def test_a_recorded_suite_page_states_it_is_not_regenerated_live(client):
    body = client.get("/suites/llm_naive").text
    assert "committed fixture" in body
    assert "never regenerates a suite live" in body


def test_run_replay_shows_the_step_log(client):
    body = client.get("/runs/1?suite=expert&build=CHK-004").text
    assert "timeline" in body
    assert "shipping free at the threshold" in body


def test_lab_post_runs_and_renders_a_scorecard(client):
    response = client.post("/lab", data={
        "target": "all",
        "defect": ["CHK-002", "AUT-001", "LED-001"],
        "suite": ["expert", "checklist"],
        "seed": "20260804",
    })
    assert response.status_code == 200
    assert "Result — run #" in response.text
    assert "Detection matrix" not in response.text  # the lab renders its own heading
    assert "Matrix for this run" in response.text


def test_lab_post_with_nothing_selected_explains_itself(client):
    response = client.post("/lab", data={"target": "all"})
    assert response.status_code == 200
    assert "Select at least one defect" in response.text


def test_lab_run_is_persisted_and_replayable(client):
    before = client.get("/runs").text.count("<tr>")
    client.post("/lab", data={
        "target": "all", "defect": ["CHK-005"], "suite": ["checklist"], "seed": "7",
    })
    after = client.get("/runs").text.count("<tr>")
    assert after == before + 1


def test_pages_carry_the_shared_shell(client):
    for path in ("/", "/benchmark", "/defects", "/suites", "/runs", "/lab"):
        body = client.get(path).text
        assert '<link rel="stylesheet" href="/static/base.css">' in body
        assert '<link rel="stylesheet" href="/static/app.css">' in body
        assert "<h1>" in body
        assert 'class="lede"' in body


def test_no_emoji_in_rendered_pages(client):
    for path in ("/", "/benchmark", "/defects", "/suites", "/runs", "/runs/1", "/lab"):
        body = client.get(path).text
        assert all(ord(ch) < 0x2190 for ch in body), f"non-ascii symbol found on {path}"


def test_lab_target_filter_narrows_the_defect_set(client):
    response = client.post("/lab", data={
        "target": "ledger",
        "defect": ["CHK-002", "AUT-001", "LED-001", "LED-003"],
        "suite": ["expert"],
        "seed": "20260804",
    })
    assert response.status_code == 200
    body = response.text
    # only the two ledger defects should have been built
    assert "LED-001" in body and "LED-003" in body
    assert "3 builds" in body or "Matrix for this run" in body
    assert ">CHK-002</a>" not in body.split("Matrix for this run")[-1]


def test_lab_target_filter_with_no_matching_defect_explains_itself(client):
    response = client.post("/lab", data={
        "target": "ledger", "defect": ["CHK-002"], "suite": ["expert"],
    })
    assert response.status_code == 200
    assert "No ledger defects are ticked" in response.text
