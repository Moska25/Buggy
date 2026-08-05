import Link from "next/link";
import Reveal from "@/components/Reveal";
import { data, pct } from "@/lib/data";

export const metadata = { title: "Runs — Buggy" };

export default function RunsPage() {
  const best = data.scores[0];

  return (
    <>
      <section className="wrap" style={{ paddingTop: 52 }}>
        <h6 className="kicker">History</h6>
        <h1 className="page-title">Every run is kept</h1>
        <p className="lede">
          Each benchmark and lab run is stored with its per-check results and step
          logs, so any run replays exactly as it was computed rather than being
          recomputed. Runs marked <em>benchmark</em> are the seeded ones
          everything else is compared against.
        </p>
      </section>

      <Reveal>
        <section className="wrap section-tight">
          <div className="tablewrap">
            <table className="table num" style={{ minWidth: 760 }}>
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Kind</th>
                  <th>Created</th>
                  <th>Seed</th>
                  <th>Builds</th>
                  <th>Results</th>
                  <th>Best recall</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <Link
                      href={`/runs/${data.run.id}`}
                      style={{ fontFamily: "var(--font-heading)", fontSize: 15 }}
                    >
                      #{data.run.id}
                    </Link>
                    <div className="muted" style={{ fontSize: 12.5 }}>
                      {data.run.label}
                    </div>
                  </td>
                  <td>
                    <span className="tag tag-accent">{data.run.kind}</span>
                  </td>
                  <td>{data.run.createdAt}</td>
                  <td>{data.run.seed}</td>
                  <td>{data.run.nBuilds}</td>
                  <td>{data.run.nResults}</td>
                  <td className="is-caught" style={{ fontWeight: 700 }}>
                    {pct(best.recall)}
                  </td>
                  <td>{data.run.durationMs} ms</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </Reveal>
    </>
  );
}
