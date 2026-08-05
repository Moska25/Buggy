import Link from "next/link";
import BoardGrid from "@/components/BoardGrid";
import BoardSwitch from "@/components/BoardSwitch";
import CatchWheel from "@/components/CatchWheel";
import Reveal from "@/components/Reveal";
import RingLegend from "@/components/RingLegend";
import Scoreboard from "@/components/Scoreboard";
import { buildWheel, data } from "@/lib/data";

export const metadata = { title: "Benchmark — Buggy" };

export default function BenchmarkPage() {
  const { cells, spokes } = buildWheel();

  return (
    <>
      <section className="wrap" style={{ paddingTop: 52 }}>
        <h6 className="kicker">
          Benchmark · run #{data.run.id} · seed {data.run.seed}
        </h6>
        <h1 className="page-title">Who caught what</h1>
        <p className="lede">
          Every defect gets its own build with exactly that defect switched on,
          plus one clean build. A check that fails on the clean build is a false
          alarm: it earns no credit anywhere, however many broken builds it also
          fails on. Without that rule a suite could top this page by asserting
          nonsense.
        </p>
        <div className="row" style={{ gap: 8, marginTop: 22 }}>
          <span className="tag tag-neutral">{data.run.nBuilds} builds</span>
          <span className="tag tag-neutral">
            {data.run.nResults} check results
          </span>
          <span className="tag tag-neutral">
            {data.run.durationMs} ms in process
          </span>
          <Link className="tag tag-outline" href={`/runs/${data.run.id}`}>
            replay the run
          </Link>
        </div>
      </section>

      <Reveal>
        <section className="wrap section-tight">
          <h2 className="h-section">Scoreboard</h2>
          <Scoreboard />
        </section>
      </Reveal>

      <Reveal>
        <section className="wrap section">
          <BoardSwitch
            wheel={
              <>
                <CatchWheel cells={cells} spokes={spokes} linkThrough />
                <div>
                  <RingLegend />
                  <p className="muted" style={{ fontSize: 13.5, marginTop: 18 }}>
                    Hover any arc to read the defect and the check that caught
                    it; click through for the full record. Rings run best-first
                    from the centre out.
                  </p>
                </div>
              </>
            }
            grid={<BoardGrid />}
          />
        </section>
      </Reveal>

      <Reveal>
        <section className="wrap section">
          <h2 className="h-section">What these numbers are not</h2>
          <div className="grid-auto" style={{ gap: 18, gridTemplateColumns: "repeat(auto-fit, minmax(min(320px, 100%), 1fr))" }}>
            <div className="tile" style={{ padding: 28 }}>
              <h4 style={{ marginBottom: 10 }}>Recall and precision</h4>
              <p className="muted" style={{ fontSize: 14.5 }}>
                Recall is defects with at least one detecting check over defects
                planted. Precision is failing results that are real detections
                over all failing results. A check that fails on the clean build
                fails on nearly every build, so it produces many spurious
                failures and correctly drags precision down.
              </p>
              <p className="muted" style={{ fontSize: 14.5, margin: 0 }}>
                &ldquo;Checks failing on clean&rdquo; counts the checks.
                &ldquo;False alarms&rdquo; counts the individual bogus reports
                they generate across the whole board — the number a human would
                actually have to triage.
              </p>
            </div>
            <div className="tile" style={{ padding: 28 }}>
              <h4 style={{ marginBottom: 10 }}>Time to detect and flake</h4>
              <p className="muted" style={{ fontSize: 14.5 }}>
                Mean time to detect accumulates in-process check duration until
                the first detecting check fires. No process start, no imports, no
                fixture setup, no I/O. It compares suites against each other and
                is <em>not</em> a CI wall-clock estimate.
              </p>
              <p className="muted" style={{ fontSize: 14.5, margin: 0 }}>
                Flake is the share of a suite&rsquo;s checks whose outcome was
                not unanimous across {data.run.repeats} repeats of the{" "}
                <Link href={`/defects/${data.ndId}`}>{data.ndId}</Link> build,
                the only nondeterministic defect. Five repeats is coarse: 0.00
                means &ldquo;nothing wobbled in five tries&rdquo;, not
                &ldquo;this suite is stable&rdquo;.
              </p>
            </div>
          </div>
        </section>
      </Reveal>
    </>
  );
}
