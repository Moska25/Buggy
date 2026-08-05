import Link from "next/link";
import { notFound } from "next/navigation";
import Reveal from "@/components/Reveal";
import {
  caught,
  checksOf,
  data,
  figureClass,
  firstCheck,
  flakeOf,
  isLoadBearing,
  pct,
  scoreOf,
  suiteById,
} from "@/lib/data";

export function generateStaticParams() {
  return data.suites.map((s) => ({ id: s.id }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const suite = data.suites.find((s) => s.id === id);
  return { title: suite ? `${suite.name} — Buggy` : "Unknown suite — Buggy" };
}

export default async function SuitePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!data.suites.some((s) => s.id === id)) notFound();

  const suite = suiteById(id);
  const s = scoreOf(id);
  const checks = checksOf(id);
  const removable = s.nChecks - s.minimal;

  const metrics = [
    {
      label: "Recall",
      value: pct(s.recall),
      cls: figureClass(s.recall),
      note: `${s.detected} of ${s.nDefects} defects found`,
    },
    {
      label: "Precision",
      value: s.precision.toFixed(2),
      cls: figureClass(s.precision, 0.9, 0.5),
      note: `${s.fpResults} of its failures were noise`,
    },
    {
      label: "False alarms",
      value: String(s.fpChecks),
      cls: s.fpChecks ? "is-missed" : "",
      note: "checks that fail on the clean build",
    },
    {
      label: "Flake",
      value: flakeOf(id),
      cls: "",
      note: `over ${data.run.repeats} repeats of the ${data.ndId} build`,
    },
  ];

  const provenance: [string, string][] = [
    ["Author", suite.authorKind],
    ["Produced", suite.producedOn],
    ["Method", suite.method],
    [
      "Could see",
      [suite.spec && "spec", suite.code && "code", suite.tools && "tools"]
        .filter(Boolean)
        .join(", "),
    ],
    [
      "Regenerated live",
      suite.recordedFixture ? "No — committed fixture" : "Not applicable",
    ],
    ["Caveat", suite.caveat],
    ["Role here", suite.expectation],
  ];

  return (
    <>
      <section className="wrap" style={{ paddingTop: 52 }}>
        <Link href="/suites" style={{ fontSize: 14 }}>
          ← all suites
        </Link>
        <h1 className="page-title" style={{ marginTop: 18 }}>
          {suite.name}
        </h1>
        <p className="lede">{suite.blurb}</p>
        {suite.recordedFixture && (
          <div
            className="panel panel-accent"
            style={{ borderRadius: 28, marginTop: 22, fontSize: 15 }}
          >
            <strong>Recorded fixture, not a live agent.</strong> {suite.caveat}
          </div>
        )}
      </section>

      <Reveal>
        <section className="wrap section-tight">
          <div
            className="grid-auto"
            style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(200px, 100%), 1fr))", gap: 14 }}
          >
            {metrics.map((m) => (
              <div key={m.label} className="tile">
                <div className="label">{m.label}</div>
                <div
                  className={`figure num ${m.cls}`}
                  style={{ fontSize: 38, marginTop: 8 }}
                >
                  {m.value}
                </div>
                <div className="muted" style={{ fontSize: 12.5, marginTop: 6 }}>
                  {m.note}
                </div>
              </div>
            ))}
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="wrap section-tight">
          <h2 className="h-section" style={{ marginBottom: 14 }}>
            Redundancy
          </h2>
          <div className={`strip ${removable ? "" : "good"}`}>
            <span className="strip-count num">
              {s.minimal}/{s.nChecks}
            </span>
            <span className="strip-what">
              {removable
                ? `${s.minimal} of its ${s.nChecks} checks carry all ${s.detected} of its detections. The other ${removable} could be deleted without this suite losing a single defect in this run.`
                : "Every check earns its place — deleting any one of them costs a detection."}
            </span>
          </div>
          <p className="muted" style={{ fontSize: 13.5, maxWidth: "76ch", marginTop: 14 }}>
            Found by delta debugging, which returns a 1-minimal set: no single
            check can be dropped from it without losing a detection. It is not
            proved globally smallest, and it is a statement about{" "}
            <Link href="/defects">these {data.defects.length} defects</Link> only
            — a check that is redundant here may be the only thing catching a
            defect this catalog does not contain.
          </p>
        </section>
      </Reveal>

      {checks.length > 0 && (
        <Reveal>
          <section className="wrap section-tight">
            <h2 className="h-section" style={{ marginBottom: 14 }}>
              All {s.nChecks} checks
            </h2>
            <div className="tablewrap">
              <table className="table" style={{ minWidth: 820 }}>
                <thead>
                  <tr>
                    <th>Id</th>
                    <th>Title</th>
                    <th>Why it exists</th>
                    <th>Load-bearing</th>
                  </tr>
                </thead>
                <tbody>
                  {checks.map((c) => (
                    <tr key={c.id}>
                      <td
                        style={{
                          fontFamily: "var(--font-heading)",
                          fontSize: 14,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {c.id}
                      </td>
                      <td>{c.title}</td>
                      <td className="muted" style={{ fontSize: 13 }}>
                        {c.intent}
                      </td>
                      <td>
                        <span
                          className={
                            isLoadBearing(c.id)
                              ? "tag tag-accent-2"
                              : "tag tag-neutral"
                          }
                        >
                          {isLoadBearing(c.id) ? "load-bearing" : "redundant here"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </Reveal>
      )}

      <Reveal>
        <section className="wrap section-tight">
          <h2 className="h-section" style={{ marginBottom: 14 }}>
            Defect by defect
          </h2>
          <div className="tablewrap">
            <table className="table" style={{ minWidth: 720 }}>
              <thead>
                <tr>
                  <th>Defect</th>
                  <th>Title</th>
                  <th>Result</th>
                  <th>Detected by</th>
                </tr>
              </thead>
              <tbody>
                {data.defects.map((d) => {
                  const hit = caught(d.id, id);
                  const cid = firstCheck(d.id, id);
                  return (
                    <tr key={d.id}>
                      <td>
                        <Link
                          href={`/defects/${d.id}`}
                          style={{ fontFamily: "var(--font-heading)", fontSize: 14 }}
                        >
                          {d.id}
                        </Link>
                      </td>
                      <td>{d.title}</td>
                      <td>
                        <span
                          className={hit ? "tag tag-accent-2" : "tag tag-outline"}
                        >
                          {hit ? "caught" : "missed"}
                        </span>
                      </td>
                      <td style={{ fontFamily: "var(--font-heading)", fontSize: 13.5 }}>
                        {cid ?? (hit ? "recorded" : "—")}
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
        <section className="wrap section-tight">
          <h2 className="h-section" style={{ marginBottom: 14 }}>
            Provenance
          </h2>
          <div
            className="panel"
            style={{
              display: "grid",
              gridTemplateColumns: "max-content minmax(0, 1fr)",
              gap: "12px 28px",
            }}
          >
            {provenance.map(([k, v]) => (
              <div key={k} style={{ display: "contents" }}>
                <div className="label" style={{ paddingTop: 3 }}>
                  {k}
                </div>
                <div className="muted" style={{ fontSize: 14.5 }}>
                  {v}
                </div>
              </div>
            ))}
          </div>
        </section>
      </Reveal>
    </>
  );
}
