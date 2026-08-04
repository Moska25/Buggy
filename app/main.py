"""FastAPI routes. Thin on purpose - every number on every page is computed in
app/runner.py or read back from SQLite, never assembled here."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db, runner
from .defects import BY_ID as DEFECT_BY_ID
from .defects import CATEGORIES, DEFECTS, NONDETERMINISTIC_ID, TARGETS, category_counts
from .suites import BY_ID as SUITE_BY_ID
from .suites import SUITE_IDS, SUITES, find_check

BASE = Path(__file__).resolve().parent
db.bootstrap()  # cheap and idempotent; keeps every route safe on a fresh checkout
app = FastAPI(title="Buggy")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))

PROJECT_NAME = "Buggy"
PROJECT_TAGLINE = "AI-native QA benchmark arena"
FOOTER_NOTE = "Seeded defects are mutants. Mutation testing, inverted to grade the tests."
NAV = [
    ("/", "Overview"),
    ("/benchmark", "Benchmark"),
    ("/defects", "Defects"),
    ("/suites", "Suites"),
    ("/runs", "Runs"),
    ("/lab", "Lab"),
]


def page(request: Request, active: str, **extra) -> dict:
    return {
        "request": request,
        "project_name": PROJECT_NAME,
        "project_tagline": PROJECT_TAGLINE,
        "footer_note": FOOTER_NOTE,
        "nav": NAV,
        "active": active,
        "suite_by_id": SUITE_BY_ID,
        "defect_by_id": DEFECT_BY_ID,
        "nd_id": NONDETERMINISTIC_ID,
        **extra,
    }


def latest() -> dict | None:
    run_id = runner.latest_run_id("benchmark")
    return runner.load_run(run_id) if run_id else None


def headline(data: dict) -> dict:
    """Facts about a stored run, derived only from what that run recorded."""
    scores = data["scores"]
    suite_ids, defect_ids = data["suite_ids"], data["defect_ids"]
    det = data["detections"]
    missed_by_all = [
        d for d in defect_ids
        if not any(det.get((s, d), {"detected": 0})["detected"] for s in suite_ids)
    ]
    caught_by_one = [
        d for d in defect_ids
        if sum(1 for s in suite_ids if det.get((s, d), {"detected": 0})["detected"]) == 1
    ]
    return {
        "best": scores[0] if scores else None,
        "worst": scores[-1] if scores else None,
        "missed_by_all": missed_by_all,
        "caught_by_one": caught_by_one,
        "total_fp": sum(s["fp_checks"] for s in scores),
        "total_checks": sum(s["n_checks"] for s in scores),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    data = latest()
    return templates.TemplateResponse(
        request,
        "index.html",
        page(request, "/", data=data, head=headline(data) if data else None,
             defects=DEFECTS, suites=SUITES, categories=category_counts(), targets=TARGETS),
    )


@app.get("/benchmark", response_class=HTMLResponse)
def benchmark(request: Request, run: int | None = None):
    run_id = run or runner.latest_run_id("benchmark")
    data = runner.load_run(run_id) if run_id else None
    return templates.TemplateResponse(
        request,
        "benchmark.html",
        page(request, "/benchmark", data=data, head=headline(data) if data else None),
    )


@app.get("/defects", response_class=HTMLResponse)
def defects_index(request: Request):
    data = latest()
    return templates.TemplateResponse(
        request,
        "defects.html",
        page(request, "/defects", data=data, defects=DEFECTS, categories=CATEGORIES,
             counts=category_counts(), targets=TARGETS),
    )


@app.get("/defects/{defect_id}", response_class=HTMLResponse)
def defect_detail(request: Request, defect_id: str):
    defect = DEFECT_BY_ID.get(defect_id)
    data = latest()
    rows = runner.detecting_checks(data["run"]["id"], defect_id) if (data and defect) else []
    return templates.TemplateResponse(
        request,
        "defect_detail.html",
        page(request, "/defects", defect=defect, data=data, rows=rows,
             find_check=find_check),
        status_code=200 if defect else 404,
    )


@app.get("/suites", response_class=HTMLResponse)
def suites_index(request: Request):
    data = latest()
    return templates.TemplateResponse(
        request,
        "suites.html", page(request, "/suites", suites=SUITES, data=data)
    )


@app.get("/suites/{suite_id}", response_class=HTMLResponse)
def suite_detail(request: Request, suite_id: str):
    suite = SUITE_BY_ID.get(suite_id)
    data = latest()
    score = next((s for s in data["scores"] if s["suite"] == suite_id), None) if (data and suite) else None
    return templates.TemplateResponse(
        request,
        "suite_detail.html",
        page(request, "/suites", suite=suite, data=data, score=score),
        status_code=200 if suite else 404,
    )


@app.get("/runs", response_class=HTMLResponse)
def runs_index(request: Request):
    return templates.TemplateResponse(
        request,
        "runs.html", page(request, "/runs", runs=runner.list_runs())
    )


@app.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(request: Request, run_id: int, suite: str | None = None, build: str | None = None):
    data = runner.load_run(run_id)
    results = []
    if data:
        suite = suite if suite in data["suite_ids"] else data["suite_ids"][0]
        builds = [runner.CLEAN, *data["defect_ids"]]
        build = build if build in builds else runner.CLEAN
        results = runner.load_results(run_id, suite=suite, build=build)
    return templates.TemplateResponse(
        request,
        "run_detail.html",
        page(request, "/runs", data=data, results=results, sel_suite=suite, sel_build=build,
             clean=runner.CLEAN, loads=db.loads, find_check=find_check),
        status_code=200 if data else 404,
    )


@app.get("/lab", response_class=HTMLResponse)
def lab(request: Request):
    return templates.TemplateResponse(
        request,
        "lab.html",
        page(request, "/lab", defects=DEFECTS, suites=SUITES, targets=TARGETS,
             report=None, sel_defects=[d.id for d in DEFECTS], sel_suites=list(SUITE_IDS),
             sel_target="all"),
    )


@app.post("/lab", response_class=HTMLResponse)
def lab_run(
    request: Request,
    target: str = Form("all"),
    defect: list[str] = Form(default=[]),
    suite: list[str] = Form(default=[]),
    seed: int = Form(runner.DEFAULT_SEED),
):
    chosen_defects = [d for d in defect if d in DEFECT_BY_ID]
    if target in TARGETS:
        chosen_defects = [d for d in chosen_defects if DEFECT_BY_ID[d].target == target]
    chosen_suites = [s for s in suite if s in SUITE_BY_ID]
    error = None
    report = None
    if not chosen_defects:
        error = ("Select at least one defect to build against."
                 if target == "all" else
                 f"No {target} defects are ticked. Tick one, or set the target back to 'all'.")
    elif not chosen_suites:
        error = "Select at least one suite to run."
    else:
        report = runner.run_and_save(
            defect_ids=chosen_defects,
            suite_ids=chosen_suites,
            seed=seed,
            kind="lab",
            label=f"Lab: {len(chosen_suites)} suite(s) against {len(chosen_defects)} defect(s)",
        )
    return templates.TemplateResponse(
        request,
        "lab.html",
        page(request, "/lab", defects=DEFECTS, suites=SUITES, targets=TARGETS,
             report=report, error=error, sel_defects=chosen_defects, sel_suites=chosen_suites,
             sel_target=target, seed=seed),
    )
