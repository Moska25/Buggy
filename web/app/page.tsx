import Link from "next/link";
import CatchWheel from "@/components/CatchWheel";
import Reveal from "@/components/Reveal";
import RingLegend from "@/components/RingLegend";
import { buildWheel, data, pct, suiteById } from "@/lib/data";

const STATS = [
  {
    value: "94.1%",
    label: "best recall",
    cls: "is-caught",
    note: "The expert suite, 16 of 17 defects found.",
  },
  {
    value: "11.8%",
    label: "worst recall",
    cls: "is-missed",
    note: "The spec checklist, 2 of 17. Same defects.",
  },
  {
    value: "35",
    label: "false alarms",
    cls: "is-mid",
    note: "Bogus failures a human would have to triage.",
  },
  {
    value: "33 ms",
    label: "whole benchmark",
    cls: "",
    note: "1296 check results, in process, reproducible.",
  },
];

const TOUR = [
  {
    n: "01",
    href: "/benchmark",
    title: "The board",
    note: "One hollow spoke all the way through: CHK-003.",
  },
  {
    n: "02",
    href: "/suites/llm_naive",
    title: "The noisy suite",
    note: "Two checks fail when nothing is wrong. Precision 0.17.",
  },
  {
    n: "03",
    href: "/defects/AUT-001",
    title: "One defect, up close",
    note: "An expired token accepted for a full hour.",
  },
  {
    n: "04",
    href: "/runs/1",
    title: "One assertion, replayed",
    note: '"shipping free at the threshold, got 4.99".',
  },
  {
    n: "05",
    href: "/lab",
    title: "The lab",
    note: "Plant one defect, change the seed, watch it wobble.",
  },
];

export default function OverviewPage() {
  const { cells, spokes } = buildWheel();

  return (
    <>
      <section className="wrap" style={{ paddingTop: 60 }}>
        <div className="row" style={{ marginBottom: 26 }}>
          <span className="tag tag-accent">
            run #{data.run.id} · seed {data.run.seed}
          </span>
          <span className="tag tag-neutral">
            {data.defects.length} defects · {data.suites.length} suites ·{" "}
            {data.run.nBuilds} builds
          </span>
        </div>

        <h1 className="display">
          One test suite caught <span className="is-caught">16 of 17</span>{" "}
          planted defects. Another caught{" "}
          <span className="is-missed">two</span>.
        </h1>

        <p className="lede lede-lg" style={{ marginBottom: 32 }}>
          Same defects. Same code. Same machine. Buggy plants seventeen small,
          believable bugs, runs four competing test suites against every single
          one, and records who noticed.
        </p>

        <div className="row" style={{ gap: 12 }}>
          <Link
            className="btn btn-primary"
            href="/benchmark"
            style={{ padding: "12px 26px", fontSize: 16, whiteSpace: "nowrap" }}
          >
            See what each suite caught
          </Link>
          <Link
            className="btn btn-secondary"
            href="/lab"
            style={{ padding: "12px 26px", fontSize: 16, whiteSpace: "nowrap" }}
          >
            Run it yourself
          </Link>
        </div>
      </section>

      <Reveal>
        <section className="wrap section-tight">
          <div className="grid-auto" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(210px, 100%), 1fr))" }}>
            {STATS.map((s) => (
              <div key={s.label} className="tile">
                <div className={`figure num ${s.cls}`}>{s.value}</div>
                <div className="label" style={{ marginTop: 12 }}>
                  {s.label}
                </div>
                <p className="muted" style={{ fontSize: 13, margin: "8px 0 0" }}>
                  {s.note}
                </p>
              </div>
            ))}
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="wrap section">
          <h6 className="kicker">The catch wheel</h6>
          <h2 className="h-section" style={{ maxWidth: "26ch", marginBottom: 14 }}>
            Every defect is a spoke. Every suite is a ring.
          </h2>
          <p className="lede" style={{ maxWidth: "58ch" }}>
            A filled arc means that suite failed on the defect&rsquo;s build and
            passed on the clean one — the only way a catch is earned here. A
            hollow arc means the bug walked straight past. Follow a spoke outward
            and you can see exactly where a defect stopped being noticed.
          </p>

          <div className="wheel" style={{ marginTop: 34 }}>
            <CatchWheel cells={cells} spokes={spokes} linkThrough />
            <div>
              <RingLegend />
              <p className="muted" style={{ fontSize: 13.5, marginTop: 18 }}>
                Rings run best-first from the centre out. The one spoke that is
                hollow all the way through is{" "}
                <Link href="/defects/CHK-003">CHK-003</Link> — a rounding mode
                nobody probed.
              </p>
            </div>
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="wrap section">
          <h6 className="kicker">What this run actually found</h6>
          <h2 className="h-section">Three findings, all computed</h2>
          <div className="grid-auto" style={{ gap: 18 }}>
            <div className="tile" style={{ padding: 28 }}>
              <div className="figure figure-xl is-missed">1</div>
              <div className="label" style={{ margin: "14px 0 10px" }}>
                defect survived every suite
              </div>
              <p className="muted" style={{ fontSize: 14, margin: 0 }}>
                <Link href="/defects/CHK-003">CHK-003</Link> rounds the total
                half-to-even instead of half-up. Only about 1% of carts show it
                at all. The expert suite missed it too.
              </p>
            </div>

            <div className="tile" style={{ padding: 28 }}>
              <div className="figure figure-xl is-mid">2</div>
              <div className="label" style={{ margin: "14px 0 10px" }}>
                caught by exactly one suite
              </div>
              <p className="muted" style={{ fontSize: 14, margin: 0 }}>
                <Link href="/defects/AUT-003">AUT-003</Link> and{" "}
                <Link href="/defects/LED-004">LED-004</Link> — the thin margin
                between &ldquo;we tested it&rdquo; and &ldquo;we would have
                shipped it&rdquo;.
              </p>
            </div>

            <div className="tile panel-accent" style={{ padding: 28 }}>
              <div
                className="figure figure-xl"
                style={{ color: "var(--color-accent-800)" }}
              >
                35
              </div>
              <div
                className="label"
                style={{ margin: "14px 0 10px", color: "var(--color-accent-800)" }}
              >
                false alarms to triage
              </div>
              <p style={{ fontSize: 14, margin: 0 }}>
                Two checks in the spec-only suite fail even when nothing is
                wrong. They earn no credit and drag its precision to{" "}
                <Link href="/suites/llm_naive">0.17</Link>.
              </p>
            </div>
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="wrap section">
          <div className="panel" style={{ padding: "34px 36px" }}>
            <h3 style={{ marginBottom: 12 }}>A planted bug is a mutant</h3>
            <p style={{ maxWidth: "70ch", fontSize: 16, margin: 0 }} className="muted">
              Mutation testing normally uses deliberate bugs to grade the code.
              Buggy turns it around and uses them to grade the tests. A suite
              only scores when it fails on a broken build <em>and</em> passes on
              the clean one. Anything else is a false alarm, not a finding — and
              that rule lives in the scoring code, not just in this paragraph.
            </p>
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="wrap section">
          <h2 className="h-section">The four suites</h2>
          <div className="tablewrap">
            <table className="table num">
              <thead>
                <tr>
                  <th>Suite</th>
                  <th>Author</th>
                  <th>Checks</th>
                  <th>Recall</th>
                  <th>Precision</th>
                  <th>False alarms</th>
                </tr>
              </thead>
              <tbody>
                {data.scores.map((s) => {
                  const suite = suiteById(s.suite);
                  return (
                    <tr key={s.suite}>
                      <td>
                        <Link href={`/suites/${s.suite}`}>{suite.name}</Link>
                      </td>
                      <td>
                        <span
                          className={
                            suite.recordedFixture
                              ? "tag tag-accent"
                              : "tag tag-neutral"
                          }
                        >
                          {suite.recordedFixture
                            ? "recorded fixture"
                            : suite.authorKind}
                        </span>
                      </td>
                      <td>{s.nChecks}</td>
                      <td style={{ fontWeight: 700 }}>{pct(s.recall)}</td>
                      <td>{s.precision.toFixed(2)}</td>
                      <td>{s.fpResults}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="wrap section">
          <h2 className="h-section" style={{ marginBottom: 8 }}>
            Five minutes, in order
          </h2>
          <p className="muted" style={{ marginBottom: 26 }}>
            If you only have a moment, take these five stops.
          </p>
          <div className="stack tour" style={{ gap: 12 }}>
            {TOUR.map((t) => (
              <Link key={t.n} href={t.href}>
                <span className="tour-n">{t.n}</span>
                <span className="tour-title">{t.title}</span>
                <span className="muted" style={{ fontSize: 14 }}>
                  {t.note}
                </span>
              </Link>
            ))}
          </div>
        </section>
      </Reveal>
    </>
  );
}
