"""Suite registry, check protocol, and suite provenance.

A check is a plain function taking a `Ctx` and using `ctx.expect(...)`. The
decorator records it in REGISTRY so the runner can execute and attribute every
check independently. Nothing here knows about defects: a check only sees
`ctx.active`, which it passes straight through to the target under test.

PROVENANCE HONESTY
------------------
Four suites ship. Two of them are labelled `llm-recorded`. Those two are
committed fixtures - Python files in this repo, authored once and checked in so
that the benchmark is reproducible and runs offline. Nothing in Buggy calls a
model at runtime, nothing requires an API key, and no suite is regenerated
live. Live generation is Phase 6 in TODO.md and is not built. The UI says the
same thing on /suites and on every suite detail page.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

REGISTRY: dict[str, list["Check"]] = {}


class CheckFailed(Exception):
    """Raised by ctx.expect when an assertion does not hold."""


@dataclass
class Ctx:
    """Execution context handed to a check. Records an ordered step log."""

    active: set[str]
    steps: list[dict[str, str]] = field(default_factory=list)

    def step(self, text: str) -> None:
        self.steps.append({"kind": "step", "text": text})

    def expect(self, condition: Any, detail: str) -> None:
        self.steps.append({"kind": "ok" if condition else "fail", "text": detail})
        if not condition:
            raise CheckFailed(detail)


@dataclass(frozen=True)
class Check:
    id: str
    suite: str
    target: str
    title: str
    intent: str
    fn: Callable[[Ctx], None]


@dataclass(frozen=True)
class Provenance:
    author_kind: str
    produced_on: str
    method: str
    spec_access: bool
    code_access: bool
    tool_access: bool
    recorded_fixture: bool
    caveat: str


@dataclass(frozen=True)
class Suite:
    id: str
    name: str
    blurb: str
    expectation: str
    provenance: Provenance

    @property
    def checks(self) -> list[Check]:
        return REGISTRY.get(self.id, [])


def check(*, suite: str, target: str, id: str, title: str, intent: str):
    """Register a check into REGISTRY under its suite."""

    def decorate(fn: Callable[[Ctx], None]) -> Callable[[Ctx], None]:
        REGISTRY.setdefault(suite, []).append(
            Check(id=id, suite=suite, target=target, title=title, intent=intent, fn=fn)
        )
        return fn

    return decorate


FIXTURE_CAVEAT = (
    "Committed fixture. This suite is a Python file in this repository, authored once "
    "and checked in. Buggy does not call any model at run time, needs no API key, and "
    "never regenerates a suite live. Live generation is an unbuilt future phase."
)

SUITES: tuple[Suite, ...] = (
    Suite(
        id="expert",
        name="Expert",
        blurb=(
            "Careful human-style checks: exact expected values, both sides of every "
            "boundary, stateful sequences, and a few invariant assertions."
        ),
        expectation="Reference ceiling. Everything else is measured against this.",
        provenance=Provenance(
            author_kind="human",
            produced_on="2026-08-04",
            method="Hand-written against the target source with the defect catalog hidden.",
            spec_access=True,
            code_access=True,
            tool_access=True,
            recorded_fixture=False,
            caveat=(
                "Written by the same author as the targets, which is a real bias: the "
                "ceiling is 'what this author thought to probe', not 'what is findable'."
            ),
        ),
    ),
    Suite(
        id="checklist",
        name="Spec checklist",
        blurb=(
            "Shallow happy-path checks read straight off the spec. Loose assertions - "
            "'the total is positive', 'the discount reduces it' - and no exact values."
        ),
        expectation="The control. This is what a suite looks like when it only looks like a suite.",
        provenance=Provenance(
            author_kind="human",
            produced_on="2026-08-04",
            method="Transcribed from the written spec bullet by bullet, without reading the code.",
            spec_access=True,
            code_access=False,
            tool_access=False,
            recorded_fixture=False,
            caveat="Deliberately shallow. Included as a floor, not as a straw man to beat.",
        ),
    ),
    Suite(
        id="llm_naive",
        name="LLM, spec only",
        blurb=(
            "Recorded output for the spec-only condition: plausible coverage, some "
            "redundancy, subtle paths missed, and two checks that assert behaviour the "
            "spec does not actually promise."
        ),
        expectation="Reads as competent. The false positives are the interesting part.",
        provenance=Provenance(
            author_kind="llm-recorded",
            produced_on="2026-08-04",
            method=(
                "Authored once as a fixture representing the spec-only condition: written "
                "from the prose specification with no access to the target source and no "
                "ability to run anything."
            ),
            spec_access=True,
            code_access=False,
            tool_access=False,
            recorded_fixture=True,
            caveat=FIXTURE_CAVEAT,
        ),
    ),
    Suite(
        id="llm_tooled",
        name="LLM, code and tools",
        blurb=(
            "Recorded output for the code-reading condition: exact expected values, real "
            "boundary probes, stateful sequences. Still blind to three defects the expert "
            "suite finds."
        ),
        expectation="The honest question: how much of the gap does tool access actually close?",
        provenance=Provenance(
            author_kind="llm-recorded",
            produced_on="2026-08-04",
            method=(
                "Authored once as a fixture representing the code-reading condition: "
                "written with the target source visible and the freedom to execute it "
                "while drafting."
            ),
            spec_access=True,
            code_access=True,
            tool_access=True,
            recorded_fixture=True,
            caveat=FIXTURE_CAVEAT,
        ),
    ),
)

BY_ID: dict[str, Suite] = {s.id: s for s in SUITES}
SUITE_IDS: tuple[str, ...] = tuple(s.id for s in SUITES)


def all_checks(suite_ids: list[str] | tuple[str, ...] | None = None) -> list[Check]:
    ids = list(suite_ids or SUITE_IDS)
    return [c for sid in ids for c in REGISTRY.get(sid, [])]


def find_check(check_id: str) -> Check | None:
    return next((c for cs in REGISTRY.values() for c in cs if c.id == check_id), None)


# Importing the suite modules is what populates REGISTRY. Kept at the bottom so
# the decorator above already exists when they import it.
from . import checklist, expert, llm_naive, llm_tooled  # noqa: E402,F401
