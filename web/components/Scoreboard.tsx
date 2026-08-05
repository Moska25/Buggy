import Link from "next/link";
import {
  data,
  figureClass,
  flakeOf,
  meterClass,
  pct,
  suiteById,
} from "@/lib/data";

/** The ranked scoreboard: recall, precision and the false-alarm count. */
export default function Scoreboard() {
  return (
    <div className="stack">
      {data.scores.map((s, i) => {
        const suite = suiteById(s.suite);
        return (
          <article
            key={s.suite}
            className={`score${s.fpResults ? " noisy" : ""}`}
          >
            <div className="score-head">
              <span className={`rank num${i === 0 ? " lead" : ""}`}>
                {String(i + 1).padStart(2, "0")}
              </span>

              <div className="score-name">
                <Link href={`/suites/${s.suite}`}>{suite.name}</Link>
                <div className="muted" style={{ fontSize: 13, marginTop: 3 }}>
                  {suite.authorKind} · {s.nChecks} checks ·{" "}
                  {suite.recordedFixture ? "recorded fixture" : "live source"}
                </div>
              </div>

              <div className="score-col">
                <div className="label">Recall</div>
                <div
                  className={`figure num ${figureClass(s.recall)}`}
                  style={{ fontSize: 38 }}
                >
                  {pct(s.recall)}
                </div>
                <div className={`meter ${meterClass(s.recall)}`} style={{ marginTop: 6 }}>
                  <span style={{ width: `${Math.round(s.recall * 100)}%` }} />
                </div>
                <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                  {s.detected} of {s.nDefects} defects found
                </div>
              </div>

              <div className="score-col" style={{ minWidth: 120 }}>
                <div className="label">Precision</div>
                <div
                  className={`figure-sm num ${figureClass(s.precision, 0.9, 0.5)}`}
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  {s.precision.toFixed(2)}
                </div>
                <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                  of its failures were real
                </div>
              </div>

              <div className={`score-fp${s.fpResults ? " noise" : ""}`}>
                <div className="label" style={{ color: "inherit", opacity: 0.75 }}>
                  False alarms
                </div>
                <div
                  className="figure-sm num"
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  {s.fpResults}
                </div>
                <div style={{ fontSize: 12, marginTop: 4, opacity: 0.8 }}>
                  {s.fpResults
                    ? `bogus reports from ${s.fpChecks} checks that fail on clean`
                    : "nothing failed on the clean build"}
                </div>
              </div>
            </div>

            <div className="score-foot num">
              <span>mean time to detect {s.mttdMs.toFixed(2)} ms</span>
              <span>runtime {s.runtimeMs.toFixed(1)} ms</span>
              <span>checks failing on clean {s.fpChecks}</span>
              <span>flake {flakeOf(s.suite)}</span>
            </div>
          </article>
        );
      })}
    </div>
  );
}
