import Link from "next/link";
import { notFound } from "next/navigation";
import Reveal from "@/components/Reveal";
import { data } from "@/lib/data";

export function generateStaticParams() {
  return [{ id: String(data.run.id) }];
}

export const metadata = { title: "Run replay — Buggy" };

/**
 * The replay of one (suite, build) pair, read back from the persisted step log.
 * The selects are presentational here: wiring them means reading
 * /runs/{id}?suite=…&build=… as searchParams and loading that slice.
 */
export default async function RunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (id !== String(data.run.id)) notFound();

  const slowest = Math.max(...data.replay.map((r) => r.us));

  return (
    <>
      <section className="wrap" style={{ paddingTop: 52, maxWidth: 1060 }}>
        <Link href="/runs" style={{ fontSize: 14 }}>
          ← run history
        </Link>
        <h6 className="kicker" style={{ marginTop: 18 }}>
          Run #{data.run.id} · expert suite · build CHK-004
        </h6>
        <h1 className="page-title">The exact line that caught it</h1>
        <p className="lede">
          Replayed from the stored step log, assertion by assertion. On this build
          the free-shipping threshold is exclusive, so a cart of exactly 50.00 is
          charged delivery — and one assertion says so in plain words.
        </p>

        <div className="row" style={{ gap: 14, marginTop: 24 }}>
          <div className="field" style={{ flex: "1 1 240px" }}>
            <label htmlFor="suite">Suite</label>
            <select id="suite" className="input" defaultValue="expert">
              {data.suites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ flex: "2 1 340px" }}>
            <label htmlFor="build">Build</label>
            <select id="build" className="input" defaultValue="CHK-004">
              <option value="clean">clean (no defect active)</option>
              {data.defects.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.id}: {d.title}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      <Reveal>
        <section className="wrap section-tight" style={{ maxWidth: 1060 }}>
          <div className="stack" style={{ gap: 14 }}>
            {data.replay.map((r, i) => (
              <article
                key={r.id}
                className={`check${r.passed ? "" : " failed"}`}
              >
                <div className="check-head">
                  <span className="check-no num">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="check-id">{r.id}</span>
                  <span
                    className={r.passed ? "tag tag-accent-2" : "tag tag-accent"}
                  >
                    {r.passed ? "pass" : "fail"}
                  </span>
                  <span className="muted" style={{ fontSize: 14 }}>
                    {r.title}
                  </span>
                  <span style={{ flex: 1 }} />
                  <span className={`check-bar${r.passed ? "" : " low"}`}>
                    <span style={{ width: `${Math.round((r.us / slowest) * 100)}%` }} />
                  </span>
                  <span className="muted num" style={{ fontSize: 12.5 }}>
                    {r.us} µs
                  </span>
                </div>

                <div className="steps">
                  {[...r.steps, ["result", r.detail] as [string, string]].map(
                    ([kind, text], j) => {
                      const bad =
                        kind === "fail" || (kind === "result" && !r.passed);
                      const ok =
                        kind === "ok" || (kind === "result" && r.passed);
                      return (
                        <div
                          key={j}
                          className={`step${bad ? " bad" : ok ? " ok" : ""}`}
                        >
                          <span className="step-kind">{kind}</span>
                          <span>{text}</span>
                        </div>
                      );
                    },
                  )}
                </div>
              </article>
            ))}
          </div>
        </section>
      </Reveal>
    </>
  );
}
