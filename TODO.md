# Buggy — roadmap

## Status

Phases 1-5 and 8-11 are built and working; phases 6 and 7 are not started. The app runs on port
8011 via `./run.sh`, seeds one full benchmark run at startup (idempotent, fixed seed 20260804),
and serves eleven routes with no unhandled exceptions. The seeded run executes 72 checks from 4
suites against 18 builds (17 seeded defects plus one clean) for 1296 check results in about
31 ms. Measured recall: Expert 94.1%, LLM code-and-tools 76.5%, LLM spec-only 41.2%, spec
checklist 11.8%; `CHK-003` is missed by every suite.

The app wears the "test harness" identity from
`MOSKA_MAIN/shared/UI_DIRECTION.md` (dot-grid wash, mono chrome, ranked scoreboard, LED detection
board, terminal status strip, instrument trace on the replay), `/` leads with the measured verdict
instead of four generic tiles, the catalog and the suite cards carry the same lit/recessed lamps as
the matrix, and `docs/screenshots/` holds the eight showcase captures.
`python -m app.cli` runs the benchmark headless, gates on recall, and exports JSON and JUnit XML;
`.github/workflows/bench.yml` fails on a recall regression against a committed baseline.
`app/minimise.py` runs ddmin over both a suite's check list and a failing cart: **15 of the expert
suite's 24 checks carry all 16 of its detections**. **The test suite is green: 172 tests, 0
failures** (`./.venv/bin/python -m pytest -q`).

Phases 6 and 7 are blocked on a decision rather than on work. Phase 6 (live LLM suite generation)
needs an API key and a policy on calling a model at run time, which would end the current
guarantee that the app runs fully offline with no key. Phase 7 (browser-layer defects) needs
Playwright as a dependency and a headless browser in CI. Neither should be started until Sandro
decides those two things.

## How to pick up a task

1. Read this file and `MOSKA_MAIN/shared/CONVENTIONS.md` before writing any code.
2. Work only the task ids you were assigned. Do not do adjacent "while I'm here" work; if you
   find something else worth doing, add it as a new task id at the end of its phase.
3. Before reporting back: run `./run.sh` and confirm the affected pages render, then run
   `./.venv/bin/python -m pytest -q` and confirm it is green. Update the `## Status` paragraph
   above with the new test count.
4. **Never run a git command.** No `add`, no `commit`, no `push`, no branches. Leave the tree
   dirty; the repository owner commits.
5. Mark finished tasks `- [x]` and leave them in place.

---

## Phase 1 — Targets and defect catalog (done)

- [x] **BUG-1.1** Implement `price_cart` in `app/targets/checkout.py` with tiers, promos,
      shipping threshold and VAT.
      Files: `app/targets/checkout.py`, `tests/test_checkout.py`
      Done when: a cart of 5 x 2.00 prices to a total of 17.39 and goods of 9.50, and quantity
      tiers apply inclusively at 3, 6 and 12 units.
- [x] **BUG-1.2** Implement `issue_token` / `verify_token` in `app/targets/authn.py` with HMAC
      signing, expiry, scope authorisation and revocation by token id.
      Files: `app/targets/authn.py`, `tests/test_authn.py`
      Done when: a token verifies at exactly `exp`, raises `AuthError` at `exp+1`, and a
      tail-tampered signature is refused.
- [x] **BUG-1.3** Implement `post_entry` / `list_entries` / `balance_of` in
      `app/targets/ledger.py` with idempotency keys, the double-entry invariant, 1-based
      pagination and per-currency balances.
      Files: `app/targets/ledger.py`, `tests/test_ledger.py`
      Done when: paging a 12-row store at `per_page=5` yields each id exactly once across three
      pages, and reposting an idempotency key leaves one row.
- [x] **BUG-1.4** Write the 17-entry defect catalog as frozen dataclasses in `app/defects.py`
      with id, target, title, description, category, severity and hint.
      Files: `app/defects.py`, `tests/test_defects.py`
      Done when: all six categories have at least one member and every hint describes the probe
      needed rather than naming it.
- [x] **BUG-1.5** Seed each defect as a single `if "<id>" in active:` branch on the real code
      path in the three target modules.
      Files: `app/targets/checkout.py`, `app/targets/authn.py`, `app/targets/ledger.py`
      Done when: `tests/test_defects.py` has one test per defect asserting both the clean and the
      defective result of the same call, and all 17 pass.
- [x] **BUG-1.6** Add the nondeterministic defect `AUT-006` driven by a runner-controlled seeded
      generator in `app/targets/rng.py`.
      Files: `app/targets/rng.py`, `app/targets/authn.py`, `tests/test_defects.py`
      Done when: a forged token is accepted on 22-38% of 400 seeded trials, and the same seed
      reproduces the same outcome every time.

## Phase 2 — Suites and registry (done)

- [x] **BUG-2.1** Build the check registry in `app/suites/__init__.py`: `Check`, `Ctx` with an
      ordered step log, `@check` decorator and `REGISTRY`.
      Files: `app/suites/__init__.py`
      Done when: `all_checks(["expert"])` returns every expert check and `Ctx.expect` records a
      step of kind `ok` or `fail` before raising.
- [x] **BUG-2.2** Write the `expert` suite: exact expected values, both sides of every boundary,
      stateful sequences, invariants.
      Files: `app/suites/expert.py`
      Done when: it scores the highest recall of any suite and produces zero false positives.
- [x] **BUG-2.3** Write the `checklist` suite: happy-path only, loose assertions, no exact values.
      Files: `app/suites/checklist.py`
      Done when: it passes on the clean build and detects no more than 3 of the 17 defects.
- [x] **BUG-2.4** Write the `llm_naive` recorded fixture, including exactly two checks that
      assert behaviour the spec does not promise.
      Files: `app/suites/llm_naive.py`
      Done when: `NAI-CHK-05` and `NAI-AUT-04` fail on the clean build, the suite's precision is
      below 0.5, and neither check is credited with any detection.
- [x] **BUG-2.5** Write the `llm_tooled` recorded fixture, stronger than naive and still blind to
      at least one defect the expert suite catches.
      Files: `app/suites/llm_tooled.py`
      Done when: its recall sits between naive and expert and
      `test_tooled_suite_misses_something_the_expert_suite_catches` passes.
- [x] **BUG-2.6** Add `Provenance` metadata to every suite and label the two fixtures as not
      regenerated live.
      Files: `app/suites/__init__.py`
      Done when: both `llm_*` suites carry `recorded_fixture=True` and a caveat stating no model
      is called at run time and no API key is needed.

## Phase 3 — Runner and scoring (done)

- [x] **BUG-3.1** Implement `runner.run` building one variant per defect plus a clean build and
      executing every check against every build.
      Files: `app/runner.py`, `tests/test_runner.py`
      Done when: a full run reports 18 builds and 1296 results, and a check that fails on the
      `CHK-002` build passes on the `CHK-004` build.
- [x] **BUG-3.2** Implement the detection rule and false-positive guard in `runner._score`.
      Files: `app/runner.py`, `tests/test_runner.py`
      Done when: a synthetic always-failing check is reported as a false positive and appears in
      the detector list of zero defects.
- [x] **BUG-3.3** Compute recall, precision, false-positive counts, mean time-to-detect and total
      runtime per suite in `runner._score`.
      Files: `app/runner.py`, `tests/test_runner.py`
      Done when: a suite detecting 2 of 3 defects reports recall 0.667, and precision equals
      true-detection failures over all failing results.
- [x] **BUG-3.4** Add flake-rate measurement to the runner.
      Files: `app/runner.py`, `tests/test_runner.py`
      Done when: a suite run against the nondeterministic defect build reports a flake rate
      strictly between 0 and 1 over 5 repeats, and the value is deterministic for a fixed seed.
- [x] **BUG-3.5** Persist runs, per-check results with step logs, scores and detections to SQLite
      in `app/db.py` and `runner.save`.
      Files: `app/db.py`, `app/runner.py`, `tests/test_runner.py`
      Done when: `runner.load_run` returns the stored scores and detections and
      `runner.load_results` returns the step log for a chosen suite and build.
- [x] **BUG-3.6** Make execution reproducible by seeding the generator from
      `crc32(seed|build|repeat|check_id)` rather than `hash()`.
      Files: `app/runner.py`, `tests/test_runner.py`
      Done when: `runner.fingerprint` is identical across two runs with the same seed, in
      separate processes.

## Phase 4 — Web app (done)

- [x] **BUG-4.1** Build the shared page shell and context helper.
      Files: `app/templates/_layout.html`, `app/main.py`, `app/static/app.css`
      Done when: every page links `base.css` then `app.css`, `--accent` is `#f59e0b`, and each
      page opens with an `h1` and a `.lede`.
- [x] **BUG-4.2** Build `/benchmark` with the detection matrix and per-suite scorecards.
      Files: `app/templates/benchmark.html`, `app/main.py`
      Done when: the page renders exactly `defects x suites` cells using `.matrix .hit` / `.miss`
      and each hit cell's `title` names the detecting check and its time-to-detect.
- [x] **BUG-4.3** Build `/defects` and `/defects/{id}`.
      Files: `app/templates/defects.html`, `app/templates/defect_detail.html`, `app/main.py`
      Done when: every catalog id returns 200, an unknown id returns 404, and the detail page
      lists which suites caught it in the latest run.
- [x] **BUG-4.4** Build `/suites` and `/suites/{id}` with the provenance panel.
      Files: `app/templates/suites.html`, `app/templates/suite_detail.html`, `app/main.py`
      Done when: both `llm_*` pages state in the HTML that the suite is a committed fixture and
      is never regenerated live, asserted by `tests/test_web.py`.
- [x] **BUG-4.5** Build `/runs` and `/runs/{id}` with the replay timeline.
      Files: `app/templates/runs.html`, `app/templates/run_detail.html`, `app/main.py`
      Done when: selecting a suite and build renders each check as a `.timeline` of its ordered
      steps, assertion details and duration.
- [x] **BUG-4.6** Build `/lab` with a form POST that runs the benchmark live and renders the
      result inline, with a target selector, per-defect toggles, suite toggles and a seed field.
      Files: `app/templates/lab.html`, `app/main.py`, `tests/test_web.py`
      Done when: posting a defect and suite selection returns 200 with a scorecard and matrix,
      narrowing the target to `ledger` builds only the ticked ledger defects, the run is
      persisted and appears in `/runs`, and an empty selection explains itself rather than
      erroring.

## Phase 5 — Seed, docs and verification (done)

- [x] **BUG-5.1** Write `app/seed.py` as an idempotent, deterministic seed.
      Files: `app/seed.py`, `run.sh`
      Done when: running it twice stores exactly one benchmark run and prints that the second
      invocation had nothing to do.
- [x] **BUG-5.2** Write `README.md` and `TODO.md` to the conventions structure.
      Files: `README.md`, `TODO.md`
      Done when: the README carries all nine required sections and every number in it was
      produced by running the code.
- [x] **BUG-5.3** Verify the definition of done from a clean state.
      Files: none
      Done when: `.venv` and `buggy.db` are deleted, `./run.sh` rebuilds and serves, every route
      returns 200, pytest is green, and `/benchmark` has no horizontal page scroll at 375px.

---

## Phase 6 — Live LLM suite generation (not started)

- [ ] **BUG-6.1** Add a suite generation script that takes a target spec and writes a suite
      module, behind an explicit opt-in flag and an API key read from the environment.
      Files: `app/generate.py` (new), `requirements.txt`
      Done when: running it with no API key present exits with a clear message and changes
      nothing, and the app still runs offline with the committed fixtures.
- [ ] **BUG-6.2** Record generation provenance (model id, timestamp, prompt digest, token counts)
      into a new `generations` table and show it on the suite page.
      Files: `app/db.py`, `app/generate.py`, `app/templates/suite_detail.html`
      Done when: a generated suite's page shows its real model id and timestamp, and a fixture
      suite still shows the `recorded fixture` label instead.
- [ ] **BUG-6.3** Add a generated-versus-fixture comparison view.
      Files: `app/templates/benchmark.html`, `app/main.py`
      Done when: the matrix can show a generated suite and its fixture counterpart side by side
      with the recall delta between them.
- [ ] **BUG-6.4** Repeat generation N times per condition and report the variance of recall.
      Files: `app/generate.py`, `app/runner.py`
      Done when: a condition run 5 times reports mean and standard deviation of recall, so the
      README can stop saying n=1.

## Phase 7 — Browser-layer defects (not started)

- [ ] **BUG-7.1** Add a minimal server-rendered checkout UI as a fourth target.
      Files: `app/targets/web_checkout.py` (new), `app/templates/target_checkout.html` (new)
      Done when: the page prices a cart through the existing `price_cart` and renders totals.
- [ ] **BUG-7.2** Seed 4 DOM-layer defects (wrong label bound to a field, a disabled submit that
      still submits, a total rendered from the pre-discount value, a form that loses state on
      validation error).
      Files: `app/defects.py`, `app/targets/web_checkout.py`
      Done when: each has a catalog entry with category `contract` or `correctness` and a test in
      `tests/test_defects.py` asserting clean and defective markup.
- [ ] **BUG-7.3** Add a Playwright-backed suite runner as an opt-in second execution mode.
      Files: `app/runner.py`, `requirements.txt`
      Done when: `pytest -q` still passes with Playwright absent, and the browser mode is skipped
      with a clear message rather than failing.

## Phase 8 — CI integration (done)

- [x] **BUG-8.1** Add a `python -m app.cli bench` entry point printing the scorecard as a table
      and exiting non-zero when any suite's recall drops below a threshold.
      Files: `app/cli.py` (new)
      Done when: `--min-recall 0.9` exits 1 for the checklist suite and 0 for the expert suite.
- [x] **BUG-8.2** Emit the detection matrix as JSON and JUnit XML.
      Files: `app/cli.py`, `tests/test_cli.py` (new)
      Done when: the JSON round-trips into `runner.load_run`-shaped data and the XML validates
      against the JUnit schema.
      **Deviation, deliberate:** the XML is checked against the JUnit *element contract*
      (nesting, required attributes, counts that agree with the cases present) rather than an
      XSD. There is no single canonical JUnit schema, and vendoring a third-party one would
      break the offline rule for no gain. See the docstring on
      `test_junit_xml_meets_the_junit_element_contract`.
- [x] **BUG-8.3** Add a GitHub Actions workflow running the benchmark and posting the recall
      delta versus the previous run as a step summary.
      Files: `.github/workflows/bench.yml` (new), `docs/bench-baseline.json` (new),
      `app/cli.py` (`compare`)
      Done when: the workflow runs offline with no secrets and fails only on a recall regression.
      The "previous run" is a committed baseline export, so the comparison works on a fresh
      clone with no CI history. `tests` and `bench` are separate jobs precisely so the bench
      job's only failure mode is a recall regression.

## Phase 9 — Delta-debugging test minimisation (done)

- [x] **BUG-9.1** Implement ddmin over a suite's check list to find the minimal subset that
      preserves a given defect's detection.
      Files: `app/minimise.py` (new), `tests/test_minimise.py` (new)
      Done when: for `CHK-004` the minimiser returns a single check and proves the subset still
      detects it.
- [x] **BUG-9.2** Report per-suite redundancy: how many checks could be deleted with no loss of
      recall.
      Files: `app/minimise.py`, `app/templates/suite_detail.html`, `app/main.py`
      Done when: each suite page shows a minimal detecting subset size alongside its check count.
      Measured: expert 15/24, llm_tooled 13/20, llm_naive 7/17, checklist 2/11.
- [x] **BUG-9.3** Minimise the failing input itself, not just the check set, for the checkout
      target.
      Files: `app/minimise.py`
      Done when: given a failing 3-line cart the minimiser returns the smallest cart that still
      exposes the defect.
      Line-level only: it drops whole lines, it does not shrink a quantity or a unit price.

---

## Phase 10 — Visual identity: "test harness" (done)

Design spec: `MOSKA_MAIN/shared/UI_DIRECTION.md`, Buggy section. This phase is a
restyle only. No runner logic, scoring rule, defect or suite may change, and every
number the site reports must be identical before and after.

- [x] **BUG-10.1** Add the dot-grid page wash and the monospace heading scale.
      Files: `app/static/app.css`
      Done when: headings render mono/uppercase with tracking, and the grid never drops
      any text below WCAG AA contrast.
- [x] **BUG-10.2** Rebuild the suite scorecard on /benchmark as a ranked scoreboard.
      Files: `app/templates/benchmark.html`, `app/static/app.css`
      Done when: suites are ordered by recall with a visible rank numeral, recall is the
      hero figure, and the spec-only suite's 35 false positives are impossible to miss.
- [x] **BUG-10.3** Restyle the detection matrix as a lit/recessed LED board.
      Files: `app/templates/benchmark.html`, `app/static/app.css`
      Done when: hit and miss differ by fill or glyph and not by colour alone, existing
      title/link behaviour still works, and the board scrolls inside `.table-wrap` at 375px.
- [x] **BUG-10.4** Add a terminal-style run status strip (run id, seed, builds, results, ms).
      Files: `app/templates/benchmark.html`, `run_detail.html`, `lab.html`, `app/static/app.css`
      Done when: the same component renders on all three pages from existing run metadata.
- [x] **BUG-10.5** Give /runs/{id} an instrument-trace feel: fixed-width step numbering,
      duration bars, pass/fail gutter.
      Files: `app/templates/run_detail.html`, `app/static/app.css`
      Done when: a long run reads as a scannable trace rather than a wall of rows.
- [x] **BUG-10.6** Rebuild `/` around the measured verdict instead of four generic metric tiles.
      Files: `app/templates/index.html`, `app/main.py` (`headline`), `app/static/app.css`
      Done when: the page opens with best-against-worst recall and the gap between them, the run's
      three findings read as figures rather than bullets, and every number on it is computed.
- [x] **BUG-10.7** Lead `/defects/{id}` with a verdict strip stating how many suites caught it.
      Files: `app/templates/defect_detail.html`, `app/main.py`, `app/static/app.css`
      Done when: `CHK-003` opens with `0/4` and the sentence "It survived every suite in this run".
- [x] **BUG-10.8** Carry the matrix's lit/recessed lamps into the catalog and the suite cards.
      Files: `app/templates/defects.html`, `app/templates/suites.html`, `app/static/app.css`
      Done when: each catalog row shows one lamp per suite in matrix order, and each suite card
      shows comparable recall and precision bars.
- [x] **BUG-10.9** Add bulk selection to the lab and retire the presentational inline styles.
      Files: `app/templates/lab.html`, all templates, `app/static/app.css`
      Done when: All / None / Only-this-target set the checkboxes without a page load, and the only
      remaining `style=` attributes are data-driven bar widths.
      Not covered by pytest (vanilla DOM); verified by driving the buttons in a real browser:
      17 defects -> 0 -> 17 -> 5 for ledger only.

## Phase 11 — Showcase assets (done)

- [x] **BUG-11.1** Capture screenshots into `docs/screenshots/`: hero (benchmark matrix),
      scoreboard, run replay, lab, plus one at 375px.
      Done when: five captioned PNGs exist, taken after Phase 10 lands.
      Eight shipped: `hero`, `overview`, `scoreboard`, `catalog`, `run-replay`, `redundancy`,
      `lab`, `mobile-375`. All 2x, all captured from the seeded run.
- [x] **BUG-11.2** Link the hero image at the top of README.md.
      Done when: the README renders the hero on GitHub without a broken image.

## Deliberately out of scope

- **Real subprocess pytest execution** - it would add seconds per run and kill the interactive
  lab, for no gain in what is being measured.
- **Multiple defects active per build** - detection could not be attributed to a single defect,
  which is the one thing the matrix has to be able to do.
- **Coverage measurement** - measuring the metric this project exists to argue against would
  invite exactly the comparison it is refuting.
- **User accounts and auth on the app itself** - it is a single-user local demo; auth would be
  scaffolding around the actual work.
- **A defect difficulty score** - any weighting would be invented rather than measured, and the
  honesty rules forbid presenting an invented number as a result.
- **Hiding the defect branches from the target source** - a blind study would need it, a
  benchmark with a public catalog does not.

## Demo script (5 minutes)

1. `./run.sh`, open **http://127.0.0.1:8011/**. Read the four metric tiles: 17 defects, 1296
   check results, best recall 94.1%, worst 11.8% - same defects, same targets.
2. Point at "What this run actually found": `CHK-003` survived every suite, and 2 defects were
   caught by exactly one suite.
3. **http://127.0.0.1:8011/benchmark** - the matrix. Hover a green cell to show the detecting
   check and its time-to-detect. Then scroll to the scorecards and stop on the LLM spec-only row:
   precision 0.17 against everyone else's 1.00.
4. **http://127.0.0.1:8011/suites/llm_naive** - explain why: two checks assert behaviour the spec
   never promised, so they fail on the clean build and produce 35 bogus failure reports. Point at
   the `recorded fixture` provenance panel and say plainly that no model is called at run time.
5. **http://127.0.0.1:8011/runs/1?suite=expert&build=CHK-004** - the replay timeline showing the
   exact assertion that caught the shipping-threshold off-by-one: "shipping free at the
   threshold, got 4.99".
6. **http://127.0.0.1:8011/lab** - untick everything except `AUT-006`, run it, change the seed,
   run it again, and watch the flaky cells move. Close on: this is why the flake column exists.

## Resume bullets

- Built a mutation-testing benchmark that grades test suites instead of code: 17 seeded defects
  across 6 categories, 4 competing suites, 72 checks executed against 18 program variants in
  ~31 ms in-process, scored on recall, precision, time-to-detect and measured flake rate.
  *(Earned by BUG-1.1 through BUG-3.6.)*
- Designed the scoring rule that makes the benchmark falsifiable - a check earns a detection only
  if it fails on the defective build and passes on the clean one - which exposed a suite scoring
  41% recall at 0.17 precision because two of its checks asserted behaviour the spec never
  promised. *(Earned by BUG-2.4, BUG-3.2, BUG-3.3.)*
- Shipped the result as a FastAPI and SQLite app with a detection matrix, per-run replay of every
  assertion and step log, and an interactive lab, with all four suites' provenance stated in the
  UI including that two are committed fixtures rather than live model output.
  *(Earned by BUG-2.6, BUG-3.5, BUG-4.1 through BUG-4.6.)*
- Applied delta debugging to the suites themselves: ddmin over each suite's check list showed
  that 15 of the expert suite's 24 checks carry all 16 of its detections, and the same algorithm
  reduces a failing cart to the single line that reproduces a pricing defect. Shipped headless as
  a CI gate with JSON and JUnit export and a recall-regression check against a committed baseline.
  *(Earned by BUG-8.1 through BUG-9.3.)*
- NOT YET EARNED: "measured how much tool access closes the gap between LLM-authored and
  expert-authored test suites, across N generations per condition" - requires BUG-6.1 through
  BUG-6.4. Today's `llm_*` suites are single hand-committed fixtures, so no claim about model
  behaviour is supportable.
