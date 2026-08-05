# Buggy — Next.js front end

The redesigned Buggy UI as a Next.js 15 App Router app, on the **Organic** design
system. Every page from the Python app is here: overview, benchmark, defect
catalog and detail, suites and detail, run history, run replay, lab.

```bash
cd nextjs
npm install
npm run dev        # http://localhost:3000
```

## What is where

```
app/
  globals.css          app layer only — layout + this app's components
  organic.css          the design system, copied verbatim. Do not edit here.
  layout.tsx           fonts (next/font), header, nav, footer
  page.tsx             overview — the scroll story
  benchmark/page.tsx   scoreboard + the board (wheel / grid)
  defects/page.tsx     catalog
  defects/[id]/        one defect: verdict, probe, per-suite result, seeding
  suites/page.tsx      the four suites
  suites/[id]/         metrics, redundancy, checks, defect-by-defect, provenance
  runs/page.tsx        history
  runs/[id]/           the replayed step log
  lab/page.tsx         client page: pick defects + suites, run, read scores
  api/lab/route.ts     proxy to the Python runner
components/
  CatchWheel.tsx       the signature graphic (client: hover + click-through)
  BoardSwitch.tsx      wheel / grid toggle
  BoardGrid.tsx        the tabular board
  RingLegend.tsx       which ring is which suite
  Scoreboard.tsx       ranked suites
  Nav.tsx              header nav with aria-current
  Reveal.tsx           scroll-in wrapper (IntersectionObserver)
lib/
  data.ts              types, lookups, formatting, wheel geometry
  run.json             run #1, seed 20260804
```

Server components render everything except the three that need interaction —
`CatchWheel`, `BoardSwitch`, `Nav`, `Reveal` and the lab page. The wheel's
geometry is computed on the server in `buildWheel()`, so the client bundle
carries hover state and nothing else.

## The catch wheel

Seventeen spokes (defects) by four rings (suites, best recall first from the
centre out). A filled arc is a detection **earned** — the check failed on that
defect's build and passed on the clean one. A hollow dashed arc is a defect that
walked past. `CHK-003` is the one spoke hollow all the way through.

Ring radii, the stagger and the arc path maths live in `lib/data.ts`
(`RING_RADII`, `arcPath`, `buildWheel`) so both pages draw the same board.

## Data

`lib/run.json` is run #1 (seed 20260804), transcribed from the repository:
`app/defects.py`, `app/suites/__init__.py`, `app/suites/expert.py`, the CLI table
pasted in the root `README.md`, and `docs/screenshots/hero.png` for the per-cell
detection matrix.

Two honest gaps carried over from the source:

- **Flake** is only published for the expert suite (`0.00`). The other three read
  `n/a` rather than a number nobody measured — see `flakeOf()`.
- **Check ids** are only committed for the expert suite, so drill-downs for the
  other three say `recorded` instead of an id — see `firstCheck()`.

To serve live data instead, replace the `run.json` import in `lib/data.ts` with a
fetch of `GET /api/runs/latest` from the FastAPI app and keep the exported
helpers as they are; every page reads through them.

## The lab

`app/lab/page.tsx` posts a selection to `app/api/lab/route.ts`, which forwards it
to the Python runner and renames the reply to this app's camelCase shape. Point
it at the service:

```bash
BUGGY_API=http://127.0.0.1:8011 npm run dev
```

The Python side needs a JSON sibling of its existing form POST — `POST /api/lab`
returning the same report object the Jinja template already receives. Until that
exists the lab renders and validates, and the run button reports that it could
not reach the runner.

## Motion and accessibility

- Arcs animate in on a stagger, meters grow, sections fade up on scroll. All of
  it is switched off under `prefers-reduced-motion: reduce` in `globals.css`.
- State is never colour alone: caught arcs are filled, missed arcs are hollow and
  dashed; grid pips carry a glyph as well as a fill.
- Focus rings come from the design system's `:focus-visible` accent ring.
- Every page holds at 375px; wide tables scroll inside `.tablewrap`.
