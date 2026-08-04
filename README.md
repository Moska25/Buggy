# Buggy

A benchmark harness that answers one question with evidence: do AI-generated tests actually
catch real defects, or do they just look like tests?

## What it does

- Hosts three small target applications (cart pricing, token auth, a double-entry ledger)
  carrying a catalog of **17 deliberately seeded defects** across six categories, each one a
  small believable branch on the real code path rather than a crash.
- Builds one variant of the system per defect - that defect active, nothing else - plus one
  clean build, then runs **four competing test suites** against all 18 builds.
- Scores each suite on recall, precision, false positives, mean time-to-detect, runtime and
  flake rate, and renders a **detection matrix** showing exactly which suite caught which defect.
- Enforces the rule that makes the whole thing meaningful: a check only earns a detection if it
  **failed on the defect build and passed on the clean build**. A check that fails on clean is a
  false positive and earns nothing.
- Persists every run, per-check result and ordered step log to SQLite, so any run replays
  exactly as it was computed.

## Why it exists / the question it answers

"We generated tests with an LLM and coverage went up" is not evidence of anything. Coverage
measures which lines ran, not whether a wrong answer would have been noticed. Buggy measures the
thing that actually matters - defect detection - by seeding known defects and checking who finds
them.

The framing that makes it credible is that **a seeded defect is a mutant**. This is mutation
testing turned around: instead of using mutants to grade the code, Buggy uses them to grade the
test suites. And because a suite can always score higher by asserting more aggressively, the
false-positive rule is enforced in the scoring code, not just described in prose.

## Run it

Requires Python 3.12 (the venv is built with `/opt/homebrew/bin/python3.12`).

```bash
./run.sh
# http://127.0.0.1:8011
```

`run.sh` creates `.venv` if missing, installs requirements, seeds one full benchmark run
(idempotent and deterministic), and starts uvicorn on port 8011.

## What to look at first

A five-minute tour, in order:

1. **http://127.0.0.1:8011/** - the headline. Best suite 94.1% recall, worst 11.8%, on identical
   defects. Every sentence in "What this run actually found" is computed from the stored run.
2. **http://127.0.0.1:8011/benchmark** - the detection matrix. Scan the `CHK-003` row: it is
   missed by all four suites, including the expert one. Hover any cell for the exact check that
   caught it and its time-to-detect.
3. **http://127.0.0.1:8011/defects/AUT-001** - an expired token accepted for a full hour. Read
   the probe: it is caught by a test at `exp+1` and missed by a test far past expiry, which is
   how most people write expiry tests.
4. **http://127.0.0.1:8011/suites/llm_naive** - precision 0.17. Two of its checks assert
   behaviour the spec never promised, so they fail on the clean build and generate 35 bogus
   failure reports. The provenance panel states plainly that this suite is a committed fixture.
5. **http://127.0.0.1:8011/lab** - untick every defect except `AUT-006`, run it, then run it
   again with a different seed and watch the flaky cells move.

## How it works

Everything runs in-process. No subprocess pytest, no Docker, no browser: 1296 check executions
complete in about 35 ms, which is what makes the lab interactive and the runs reproducible.

```
app/targets/*.py        real logic + `if "CHK-003" in active:` seeded branches
        |
        v
app/runner.py           for each defect -> build with only that defect active
                        for each check  -> execute, capture pass/fail/detail/steps/duration
                        detection = fail(defect build) AND pass(clean build)
        |
        +--> app/suites/    expert | checklist | llm_naive | llm_tooled  (registry of checks)
        |
        v
SQLite (runs, results, scores, detections)  ->  FastAPI + Jinja2  ->  /benchmark, /runs/{id}
```

The only nondeterminism is one seeded defect (`AUT-006`) that skips signature verification on
~30% of calls. It reads from a generator the runner reseeds per execution, keyed on
`(seed, build, repeat, check id)` via crc32 - never Python's salted `hash()`. So a run is exactly
reproducible from its seed while repeats of the same build genuinely differ, which is what makes
the flake column a measurement rather than a constant.

## Engineering notes

- **The false-positive rule is the design.** Early on, a suite that asserted nonsense scored well
  because it failed on every defective build. Detection now requires passing on clean, checked in
  `runner._score`, and `tests/test_runner.py` verifies an always-failing check earns zero
  detections. Precision is defined as *failing results that are true detections over all failing
  results*, so a clean-failing check drags it down in proportion to the triage burden it creates.
- **Time-to-detect is honest about what it is not.** It accumulates in-process check duration in
  registration order until the first detecting check fires. There is no process start, no import,
  no fixture setup, no I/O - so it compares suites against each other and must not be read as a
  CI wall-clock estimate. The UI says so next to the number.
- **The rounding defect was chosen by brute force, not by vibes.** `CHK-003` swaps half-up for
  banker's rounding on the final quantize. Measured across 19,995 single-line carts it changes
  the total on 1.00% of them. The one cart that exposes it (5 x 1.41) was found by solving for a
  total landing on an exact half-cent tie with an even preceding digit. Every suite misses it,
  which is the most useful result on the page.
- **Defects are seeded as branches, not patches.** `if "LED-001" in active:` inside the real
  function means one process holds all 18 variants, no file rewriting and no import juggling, and
  a build is a `set[str]`. The cost is that the defect is visible in the source, which would be
  wrong for a blind study and is fine for a benchmark whose catalog is public anyway.
- **Flake needs a real generator.** An early version faked flake as a constant. It is now
  measured from outcome instability across 5 repeats, and `tests/test_defects.py` asserts the
  defect fires on 22-38% of 400 seeded trials - a genuinely intermittent mechanism rather than a
  decorative column.

### Honesty about the two LLM suites

`llm_naive` and `llm_tooled` are **committed fixtures**: Python files in this repository,
authored once to represent their two conditions (spec-only, and code-reading) and checked in so
the benchmark is reproducible and runs offline.

**Buggy does not call a model at run time, requires no API key, and never regenerates a suite
live.** Nothing in the UI is the output of an agent running now. Both suites are labelled
`recorded fixture` on `/suites`, on their detail pages, and in the lab. Live generation is Phase
6 in `TODO.md` (BUG-6.1 to BUG-6.4) and is not built.

## Tests

```bash
./.venv/bin/python -m pytest -q      # 145 tests, all passing
```

What they cover:

- **Clean target behaviour** (`test_checkout.py`, `test_authn.py`, `test_ledger.py`) - the
  contract each defect is measured against: exact totals, both sides of every boundary, expiry
  edges, revocation, pagination continuity, the double-entry invariant.
- **Every seeded defect** (`test_defects.py`) - one test per defect asserting both the clean and
  the defective result of the same call. If a defect ever stops being observable, the matrix
  would silently start lying; this file is the guard against that.
- **The runner** (`test_runner.py`) - the detection rule via a synthetic suite with known
  behaviour (an always-failing check earns zero detections and is recorded as a false positive),
  recall and precision arithmetic, build isolation, step-log capture, SQLite round-trip, and
  byte-identical fingerprints for a fixed seed.
- **Routes** (`test_web.py`) - every page 200, unknown ids 404, the matrix renders exactly
  `defects x suites` cells, the lab POST runs and persists, and the recorded-fixture labelling is
  actually present in the HTML.

Deliberately not covered: CSS and layout (verified by hand at 375px and 1280px), uvicorn startup,
and concurrent access to the SQLite file - the app is single-process by design.

## Limitations

- **The suites are fixtures, not a study.** Four suites, one author, one sitting. This
  demonstrates a measurement apparatus; it is not evidence about any particular model. The
  `llm_*` suites represent their conditions, they are not a controlled experiment, and n=1.
- **The expert suite is written by the author of the targets.** That is a real ceiling bias: it
  measures "what this author thought to probe", not "what is findable". It is stated on
  `/suites/expert` too.
- **17 defects is a small sample.** A single defect moves recall by 5.9 points, so small
  differences between suites are noise. The matrix is more informative than the percentages.
- **Flake over 5 repeats is a coarse estimator.** A reading of 0.00 means "nothing wobbled in
  five tries", not "this suite is stable". The expert suite reads 0.00 here partly by luck.
- **Pure-logic targets only.** No HTTP layer, no database under test, no browser, no concurrency.
  Whole classes of real defect - race conditions, N+1 queries, DOM-level breakage - cannot be
  seeded in this design at all.
- **Defects are seeded one at a time.** Interacting defects, which are where real debugging time
  goes, are out of scope; a build carries exactly one.
- **Mean time-to-detect is in-process cost.** It is useful for comparing suites and useless as a
  CI estimate.
