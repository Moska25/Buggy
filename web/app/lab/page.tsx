"use client";

import { useState } from "react";
import Reveal from "@/components/Reveal";
import {
  data,
  defectsFor,
  meterClass,
  pct,
  scoreOf,
  suiteById,
  targetIds,
} from "@/lib/data";

interface LabScore {
  suite: string;
  nChecks: number;
  detected: number;
  nDefects: number;
  recall: number;
  precision: number;
  mttdMs: number;
}

interface LabReport {
  runId: number;
  seed: number;
  nBuilds: number;
  nResults: number;
  durationMs: number;
  scores: LabScore[];
}

const ALL_DEFECTS = data.defects.map((d) => d.id);
const ALL_SUITES = [...data.suiteOrder];

export default function LabPage() {
  const [defects, setDefects] = useState<string[]>(ALL_DEFECTS);
  const [suites, setSuites] = useState<string[]>(ALL_SUITES);
  const [seed, setSeed] = useState(String(data.run.seed));
  const [target, setTarget] = useState("all");
  const [report, setReport] = useState<LabReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const toggle = (
    list: string[],
    set: (v: string[]) => void,
    id: string,
  ) => () => set(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

  async function run() {
    setError(null);
    if (!defects.length) return setError("Plant at least one defect.");
    if (!suites.length) return setError("Select at least one suite to run.");

    setPending(true);
    try {
      const res = await fetch("/api/lab", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          defects,
          suites,
          seed: Number(seed) || data.run.seed,
          target,
        }),
      });
      if (!res.ok) {
        /* the route explains itself when no runner is configured */
        const said = await res.json().catch(() => null);
        throw new Error(said?.error ?? `runner replied ${res.status}`);
      }
      setReport((await res.json()) as LabReport);
    } catch (e) {
      setError(e instanceof Error ? e.message : "unknown error");
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <section className="wrap" style={{ paddingTop: 52 }}>
        <h6 className="kicker">Lab</h6>
        <h1 className="page-title">
          Change the conditions, watch the scores move
        </h1>
        <p className="lede">
          Pick which defects to plant and which suites to run. This executes for
          real, in process, against a fresh build per defect plus one clean build,
          scored by the same rule as the seeded benchmark. A whole run takes tens
          of milliseconds.
        </p>
      </section>

      <Reveal>
        <section className="wrap section-tight">
          <div className="panel">
            <div className="row" style={{ alignItems: "baseline", gap: 12 }}>
              <h3 style={{ margin: 0 }}>Suites</h3>
              <span className="muted" style={{ fontSize: 13 }}>
                Unticking a suite removes it from the scorecard entirely.
              </span>
            </div>
            <div
              className="toggles"
              style={{ gridTemplateColumns: "repeat(auto-fill, minmax(min(260px, 100%), 1fr))" }}
            >
              {data.suites.map((s) => {
                const on = suites.includes(s.id);
                return (
                  <label key={s.id} className={`toggle${on ? " on" : ""}`}>
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={toggle(suites, setSuites, s.id)}
                    />
                    <span style={{ fontSize: 14.5 }}>
                      <strong>{s.name}</strong> · {scoreOf(s.id).nChecks} checks
                    </span>
                    {s.recordedFixture && (
                      <span className="tag tag-accent">fixture</span>
                    )}
                  </label>
                );
              })}
            </div>
          </div>

          <div className="panel" style={{ marginTop: 16 }}>
            <div className="row">
              <h3 style={{ margin: 0, flex: "1 1 auto" }}>Defects to plant</h3>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setDefects(ALL_DEFECTS)}
              >
                All
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setDefects([])}
              >
                None
              </button>
            </div>

            {targetIds.map((t) => (
              <div key={t} style={{ marginTop: 22 }}>
                <div className="group-head">
                  <span className="group-name">{t}</span>
                  <span className="muted" style={{ fontSize: 13, flex: "1 1 auto" }}>
                    {data.targets[t]}
                  </span>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => setDefects(defectsFor(t).map((d) => d.id))}
                  >
                    Only this target
                  </button>
                </div>
                <div className="toggles">
                  {defectsFor(t).map((d) => {
                    const on = defects.includes(d.id);
                    return (
                      <label key={d.id} className={`toggle${on ? " on" : ""}`}>
                        <input
                          type="checkbox"
                          checked={on}
                          onChange={toggle(defects, setDefects, d.id)}
                        />
                        <span>
                          <strong>{d.id}</strong> {d.title}
                        </span>
                        {d.id === data.ndId && (
                          <span className="tag tag-accent">flaky</span>
                        )}
                      </label>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          <div
            className="panel row"
            style={{ marginTop: 16, gap: 16, alignItems: "flex-end" }}
          >
            <div className="field" style={{ flex: "1 1 200px" }}>
              <label htmlFor="target">Target</label>
              <select
                id="target"
                className="input"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              >
                <option value="all">all three targets</option>
                {targetIds.map((t) => (
                  <option key={t} value={t}>
                    {t} only
                  </option>
                ))}
              </select>
            </div>
            <div className="field" style={{ flex: "1 1 160px" }}>
              <label htmlFor="seed">Seed</label>
              <input
                id="seed"
                className="input num"
                type="number"
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
              />
            </div>
            <button
              type="button"
              className="btn btn-primary"
              onClick={run}
              disabled={pending}
              style={{ padding: "12px 28px", fontSize: 16 }}
            >
              {pending ? "Running…" : "Run benchmark"}
            </button>
            <p className="muted" style={{ flex: "1 1 100%", fontSize: 13, margin: 0 }}>
              The seed drives the one nondeterministic defect ({data.ndId}). The
              same seed reproduces the same run exactly, so change it and the
              flaky cells move.
            </p>
          </div>

          {error && (
            <div
              className="panel panel-accent"
              style={{ marginTop: 16, borderRadius: 28, fontSize: 15 }}
            >
              <strong>Nothing ran.</strong> {error}
            </div>
          )}
        </section>
      </Reveal>

      {report && (
        <section className="wrap section-tight">
          <h2 className="h-section" style={{ marginBottom: 8 }}>
            Result: run #{report.runId}
          </h2>
          <div className="row" style={{ gap: 8, marginBottom: 18 }}>
            <span className="tag tag-neutral">seed {report.seed}</span>
            <span className="tag tag-neutral">{report.nBuilds} builds</span>
            <span className="tag tag-neutral">{report.nResults} check results</span>
            <span className="tag tag-neutral">
              {report.durationMs} ms in process
            </span>
          </div>
          <div className="tablewrap">
            <table className="table num" style={{ minWidth: 680 }}>
              <thead>
                <tr>
                  <th>Suite</th>
                  <th>Checks</th>
                  <th>Found</th>
                  <th>Recall</th>
                  <th>Precision</th>
                  <th>Mean TTD</th>
                </tr>
              </thead>
              <tbody>
                {report.scores.map((s) => (
                  <tr key={s.suite}>
                    <td>{suiteById(s.suite).name}</td>
                    <td>{s.nChecks}</td>
                    <td>
                      {s.detected}/{s.nDefects}
                    </td>
                    <td>
                      <div className="row" style={{ gap: 10 }}>
                        <span
                          className={`meter ${meterClass(s.recall)}`}
                          style={{ flex: 1, minWidth: 60 }}
                        >
                          <span style={{ width: `${Math.round(s.recall * 100)}%` }} />
                        </span>
                        <span style={{ whiteSpace: "nowrap" }}>{pct(s.recall)}</span>
                      </div>
                    </td>
                    <td>{s.precision.toFixed(2)}</td>
                    <td>{s.mttdMs.toFixed(2)} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
