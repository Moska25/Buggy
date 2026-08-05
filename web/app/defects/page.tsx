import Link from "next/link";
import Reveal from "@/components/Reveal";
import {
  catchCount,
  caught,
  data,
  defectsFor,
  severityTag,
  suiteById,
  targetIds,
} from "@/lib/data";

export const metadata = { title: "Defects — Buggy" };

export default function DefectsPage() {
  return (
    <>
      <section className="wrap" style={{ paddingTop: 52 }}>
        <h6 className="kicker">Catalog</h6>
        <h1 className="page-title">Seventeen planted defects</h1>
        <p className="lede">
          Each one is a small, believable branch inside the real code path — a
          rounding mode, an off-by-one, a narrowed guard. None of them crash. A
          suite does not miss a defect because it is bad; it misses because it
          never built the input that would show it, and every record here says
          which input that is.
        </p>
      </section>

      <Reveal>
        <section className="wrap section-tight">
          <div className="grid-auto">
            {targetIds.map((t) => (
              <div key={t} className="tile" style={{ padding: 24 }}>
                <div
                  style={{
                    fontFamily: "var(--font-heading)",
                    fontSize: 20,
                    color: "var(--color-accent-700)",
                  }}
                >
                  {t}
                </div>
                <div
                  className="num"
                  style={{
                    fontFamily: "var(--font-heading)",
                    fontSize: 36,
                    marginTop: 6,
                  }}
                >
                  {defectsFor(t).length} defects
                </div>
                <p className="muted" style={{ fontSize: 13.5, margin: "8px 0 0" }}>
                  {data.targets[t]}
                </p>
              </div>
            ))}
          </div>

          <div className="row" style={{ gap: 8, marginTop: 20 }}>
            {data.categories.map((c) => (
              <span key={c} className="tag tag-accent-2">
                {c} · {data.defects.filter((d) => d.category === c).length}
              </span>
            ))}
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="wrap section-tight">
          <div className="tablewrap">
            <table className="table" style={{ minWidth: 780 }}>
              <thead>
                <tr>
                  <th>Id</th>
                  <th>Title</th>
                  <th>Target</th>
                  <th>Kind</th>
                  <th>Severity</th>
                  <th className="right">Caught by</th>
                </tr>
              </thead>
              <tbody>
                {data.defects.map((d) => {
                  const n = catchCount(d.id);
                  return (
                    <tr key={d.id}>
                      <td>
                        <Link
                          href={`/defects/${d.id}`}
                          style={{
                            fontFamily: "var(--font-heading)",
                            fontSize: 15,
                          }}
                        >
                          {d.id}
                        </Link>
                      </td>
                      <td style={{ maxWidth: "34ch" }}>{d.title}</td>
                      <td className="muted" style={{ fontSize: 13 }}>
                        {d.target}
                      </td>
                      <td>
                        <span className="tag tag-neutral">{d.category}</span>
                      </td>
                      <td>
                        <span className={severityTag(d.severity)}>
                          {d.severity}
                        </span>
                      </td>
                      <td>
                        <div
                          className="row"
                          style={{ justifyContent: "flex-end", gap: 5 }}
                        >
                          {data.suiteOrder.map((sid) => {
                            const hit = caught(d.id, sid);
                            return (
                              <span
                                key={sid}
                                className={`pip-sm${hit ? "" : " miss"}`}
                                title={`${suiteById(sid).name} ${
                                  hit ? "caught it" : "missed it"
                                }`}
                              />
                            );
                          })}
                          <span
                            className={`pip-count num${n ? "" : " none"}`}
                          >
                            {n}/{data.suiteOrder.length}
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </Reveal>
    </>
  );
}
