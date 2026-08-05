import Link from "next/link";
import { notFound } from "next/navigation";
import Reveal from "@/components/Reveal";
import {
  catchCount,
  caught,
  data,
  defectById,
  firstCheck,
  scoreOf,
  severityTag,
  suiteById,
} from "@/lib/data";

export function generateStaticParams() {
  return data.defects.map((d) => ({ id: d.id }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const defect = defectById(id);
  return { title: defect ? `${defect.id} — Buggy` : "Unknown defect — Buggy" };
}

export default async function DefectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const defect = defectById(id);
  if (!defect) notFound();

  const n = catchCount(defect.id);
  const tone = n === 0 ? "bad" : n === data.suiteOrder.length ? "good" : "";
  const verdict =
    n === 0
      ? "It survived every suite in this run, the expert one included. This is the defect that would have shipped."
      : n === data.suiteOrder.length
        ? "Every suite caught it. The probe that exposes it is one they all already build."
        : `${n} of ${data.suiteOrder.length} suites caught it. The other ${
            data.suiteOrder.length - n
          } never built the input described below.`;

  return (
    <>
      <section className="wrap" style={{ paddingTop: 52, maxWidth: 980 }}>
        <Link href="/defects" style={{ fontSize: 14 }}>
          ← all defects
        </Link>

        <div className="row" style={{ gap: 8, margin: "20px 0 16px" }}>
          <span className="tag tag-neutral">{defect.category}</span>
          <span className={severityTag(defect.severity)}>{defect.severity}</span>
          <span className="tag tag-outline">{defect.target}</span>
          {defect.id === data.ndId && (
            <span className="tag tag-accent">nondeterministic</span>
          )}
        </div>

        <h6 className="kicker">{defect.id}</h6>
        <h1 className="page-title">{defect.title}</h1>
        <p className="lede">{defect.description}</p>

        <div className={`strip ${tone}`} style={{ marginTop: 28 }}>
          <span className="strip-count num">
            {n}/{data.suiteOrder.length}
          </span>
          <span className="strip-what">{verdict}</span>
        </div>
      </section>

      <Reveal>
        <section className="wrap section-tight" style={{ maxWidth: 980 }}>
          <h2 className="h-section" style={{ marginBottom: 14 }}>
            The probe you would need
          </h2>
          <div
            className="panel panel-accent"
            style={{ borderRadius: 28, fontSize: 16, lineHeight: 1.55 }}
          >
            {defect.hint}
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="wrap section-tight" style={{ maxWidth: 980 }}>
          <h2 className="h-section" style={{ marginBottom: 14 }}>
            Which suites caught it
          </h2>
          <div className="tablewrap">
            <table className="table" style={{ minWidth: 620 }}>
              <thead>
                <tr>
                  <th>Suite</th>
                  <th>Result</th>
                  <th>First detecting check</th>
                  <th className="right">Time to detect</th>
                </tr>
              </thead>
              <tbody>
                {data.suiteOrder.map((sid) => {
                  const hit = caught(defect.id, sid);
                  const cid = firstCheck(defect.id, sid);
                  const check = data.expertChecks.find((c) => c.id === cid);
                  return (
                    <tr key={sid}>
                      <td>
                        <Link href={`/suites/${sid}`}>
                          {suiteById(sid).name}
                        </Link>
                      </td>
                      <td>
                        <span
                          className={
                            hit ? "tag tag-accent-2" : "tag tag-outline"
                          }
                        >
                          {hit ? "caught" : "missed"}
                        </span>
                      </td>
                      <td>
                        <span
                          style={{
                            fontFamily: "var(--font-heading)",
                            fontSize: 14,
                          }}
                        >
                          {cid ?? (hit ? "recorded" : "—")}
                        </span>
                        {check && (
                          <div className="muted" style={{ fontSize: 12.5 }}>
                            {check.title}
                          </div>
                        )}
                      </td>
                      <td className="right num">
                        {hit ? `${scoreOf(sid).mttdMs.toFixed(2)} ms` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="wrap section-tight" style={{ maxWidth: 980 }}>
          <h2 className="h-section" style={{ marginBottom: 14 }}>
            How it is planted
          </h2>
          <div className="panel">
            <p className="muted" style={{ fontSize: 15.5 }}>
              It lives in{" "}
              <span style={{ fontFamily: "var(--font-heading)", fontSize: 14 }}>
                app/targets/{defect.target}.py
              </span>{" "}
              as a branch on the active defect set. The runner builds one variant
              with exactly {defect.id} switched on and nothing else, so a
              detection can only be attributed to this defect.
            </p>
            <pre className="code">
              {`if "${defect.id}" in active:\n    ...  # the planted behaviour`}
            </pre>
            <p style={{ fontSize: 14, margin: "16px 0 0" }}>
              <Link href="/lab">Run this defect on its own in the lab →</Link>
            </p>
          </div>
        </section>
      </Reveal>
    </>
  );
}
