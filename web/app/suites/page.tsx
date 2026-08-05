import Link from "next/link";
import Reveal from "@/components/Reveal";
import { data, figureClass, meterClass, pct, scoreOf } from "@/lib/data";

export const metadata = { title: "Suites — Buggy" };

export default function SuitesPage() {
  return (
    <>
      <section className="wrap" style={{ paddingTop: 52 }}>
        <h6 className="kicker">Suites</h6>
        <h1 className="page-title">Four suites, one variable</h1>
        <p className="lede">
          The same three targets and the same planted defects for all of them.
          The only thing that changes is who wrote the checks and what they could
          see while writing them.
        </p>
        <div
          className="panel panel-accent"
          style={{ borderRadius: 28, marginTop: 26, fontSize: 15, lineHeight: 1.55 }}
        >
          <strong>Provenance, stated plainly.</strong> The two suites marked{" "}
          <em>recorded fixture</em> are Python files committed to this
          repository, authored once to represent their condition — spec-only, and
          code-reading — and checked in so the benchmark is reproducible and runs
          offline. Buggy never calls a model at run time, needs no API key, and
          does not regenerate a suite live. Nothing here is the output of an agent
          running now.
        </div>
      </section>

      <Reveal>
        <section className="wrap section-tight">
          <div className="grid-auto grid-wide" style={{ gap: 18 }}>
            {data.suites.map((suite) => {
              const s = scoreOf(suite.id);
              return (
                <article key={suite.id} className="panel">
                  <div className="row">
                    <h3 style={{ margin: 0, flex: "1 1 auto" }}>
                      <Link href={`/suites/${suite.id}`} style={{ color: "inherit" }}>
                        {suite.name}
                      </Link>
                    </h3>
                    <span
                      className={
                        suite.recordedFixture ? "tag tag-accent" : "tag tag-neutral"
                      }
                    >
                      {suite.recordedFixture
                        ? "recorded fixture"
                        : `${suite.authorKind}-authored`}
                    </span>
                    <span className="tag tag-neutral">{s.nChecks} checks</span>
                  </div>

                  <p className="muted" style={{ fontSize: 14.5, margin: "14px 0 0" }}>
                    {suite.blurb}
                  </p>
                  <p
                    className="muted"
                    style={{ fontSize: 13.5, margin: "8px 0 0", opacity: 0.8 }}
                  >
                    {suite.expectation}
                  </p>

                  <div
                    className="row"
                    style={{ alignItems: "baseline", gap: 26, marginTop: 20 }}
                  >
                    <div>
                      <div className="label">Recall</div>
                      <div
                        className={`num ${figureClass(s.recall)}`}
                        style={{ fontFamily: "var(--font-heading)", fontSize: 34 }}
                      >
                        {pct(s.recall)}
                      </div>
                    </div>
                    <div>
                      <div className="label">Precision</div>
                      <div
                        className={`num ${figureClass(s.precision, 0.9, 0.5)}`}
                        style={{ fontFamily: "var(--font-heading)", fontSize: 34 }}
                      >
                        {s.precision.toFixed(2)}
                      </div>
                    </div>
                    <div style={{ flex: 1, minWidth: 140 }}>
                      <div className={`meter ${meterClass(s.recall)}`}>
                        <span style={{ width: `${Math.round(s.recall * 100)}%` }} />
                      </div>
                      <div className="muted" style={{ fontSize: 12.5, marginTop: 7 }}>
                        {s.detected} of {s.nDefects} defects found
                      </div>
                    </div>
                  </div>

                  <div className="row" style={{ gap: 8, marginTop: 20 }}>
                    {(
                      [
                        ["spec", suite.spec],
                        ["code", suite.code],
                        ["tools", suite.tools],
                      ] as const
                    ).map(([label, on]) => (
                      <span
                        key={label}
                        className={on ? "tag tag-accent-2" : "tag tag-neutral"}
                      >
                        {label} {on ? "yes" : "no"}
                      </span>
                    ))}
                    <span
                      className="muted num"
                      style={{ fontSize: 12, alignSelf: "center" }}
                    >
                      {suite.producedOn}
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </Reveal>
    </>
  );
}
