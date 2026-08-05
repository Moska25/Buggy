import { NextResponse } from "next/server";

/**
 * Proxy for the lab. The benchmark itself stays in the Python runner
 * (app/runner.py) — this route forwards a selection to it and normalises the
 * reply into the shape app/lab/page.tsx expects.
 *
 * Set BUGGY_API to the FastAPI origin, e.g. http://127.0.0.1:8011
 */
const API = process.env.BUGGY_API;

interface Body {
  defects: string[];
  suites: string[];
  seed: number;
  target: string;
}

export async function POST(request: Request) {
  /* Say so plainly rather than failing with a connection error: on a static
     host there is no runner behind this route until BUGGY_API points at one. */
  if (!API) {
    return NextResponse.json(
      {
        error:
          "no runner is reachable from this deployment. The lab executes in the " +
          "Python runner; set BUGGY_API to a reachable FastAPI origin, or run the " +
          "repo locally with ./run.sh.",
      },
      { status: 503 },
    );
  }

  const body = (await request.json()) as Body;

  const form = new URLSearchParams();
  form.set("target", body.target || "all");
  form.set("seed", String(body.seed));
  body.defects.forEach((d) => form.append("defect", d));
  body.suites.forEach((s) => form.append("suite", s));

  const res = await fetch(`${API}/api/lab`, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: form,
    cache: "no-store",
  });

  if (!res.ok) {
    return NextResponse.json(
      { error: `runner replied ${res.status}` },
      { status: 502 },
    );
  }

  /* The runner's report, renamed to this app's camelCase shape. */
  const report = (await res.json()) as {
    run_id: number;
    seed: number;
    n_builds: number;
    duration_ms: number;
    results: unknown[];
    scores: {
      suite: string;
      n_checks: number;
      detected: number;
      n_defects: number;
      recall: number;
      precision: number;
      mttd_ms: number;
    }[];
  };

  return NextResponse.json({
    runId: report.run_id,
    seed: report.seed,
    nBuilds: report.n_builds,
    nResults: report.results.length,
    durationMs: Math.round(report.duration_ms),
    scores: report.scores.map((s) => ({
      suite: s.suite,
      nChecks: s.n_checks,
      detected: s.detected,
      nDefects: s.n_defects,
      recall: s.recall,
      precision: s.precision,
      mttdMs: s.mttd_ms,
    })),
  });
}
