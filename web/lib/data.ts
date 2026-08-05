import raw from "./run.json";

/* ── types ─────────────────────────────────────────────────── */

export type TargetId = "checkout" | "authn" | "ledger";
export type Severity = "blocker" | "major" | "minor";

export interface Defect {
  id: string;
  target: TargetId;
  category: string;
  severity: Severity;
  title: string;
  description: string;
  hint: string;
}

export interface Suite {
  id: string;
  name: string;
  authorKind: string;
  recordedFixture: boolean;
  blurb: string;
  expectation: string;
  producedOn: string;
  spec: boolean;
  code: boolean;
  tools: boolean;
  method: string;
  caveat: string;
}

export interface Score {
  suite: string;
  nChecks: number;
  detected: number;
  nDefects: number;
  recall: number;
  precision: number;
  fpChecks: number;
  fpResults: number;
  mttdMs: number;
  runtimeMs: number;
  /** checks ddmin keeps: the 1-minimal set preserving every detection */
  minimal: number;
}

export interface Check {
  id: string;
  target: TargetId;
  title: string;
  intent: string;
}

export interface ReplayStep {
  0: "step" | "ok" | "fail";
  1: string;
}

export interface ReplayCheck {
  id: string;
  passed: boolean;
  us: number;
  title: string;
  steps: [string, string][];
  detail: string;
}

export interface Run {
  id: number;
  seed: number;
  kind: string;
  createdAt: string;
  label: string;
  nBuilds: number;
  nResults: number;
  nChecks: number;
  durationMs: number;
  repeats: number;
}

interface Data {
  projectName: string;
  tagline: string;
  footerNote: string;
  targets: Record<TargetId, string>;
  categories: string[];
  defects: Defect[];
  suites: Suite[];
  /** ranked by recall, then precision — the order the scoreboard uses */
  scores: Score[];
  /** defect id → suite ids that earned a detection on it */
  hits: Record<string, string[]>;
  expertChecks: Check[];
  expertFirst: Record<string, string>;
  expertKeep: string[];
  replay: ReplayCheck[];
  run: Run;
  ndId: string;
  /** registry order — the order columns appear on the grid board */
  suiteOrder: string[];
}

export const data = raw as unknown as Data;

/* ── lookups ───────────────────────────────────────────────── */

export const suiteById = (id: string): Suite =>
  data.suites.find((s) => s.id === id)!;

export const defectById = (id: string): Defect | undefined =>
  data.defects.find((d) => d.id === id);

export const scoreOf = (suiteId: string): Score =>
  data.scores.find((s) => s.suite === suiteId)!;

export const caught = (defectId: string, suiteId: string): boolean =>
  (data.hits[defectId] ?? []).includes(suiteId);

export const catchCount = (defectId: string): number =>
  (data.hits[defectId] ?? []).length;

/** The suite that first detected a defect, where the repo records it. */
export const firstCheck = (defectId: string, suiteId: string): string | null =>
  suiteId === "expert" ? data.expertFirst[defectId] ?? null : null;

export const checksOf = (suiteId: string): Check[] =>
  suiteId === "expert" ? data.expertChecks : [];

export const isLoadBearing = (checkId: string): boolean =>
  data.expertKeep.includes(checkId);

/** Only the expert suite's flake reading is in the committed CLI output. */
export const flakeOf = (suiteId: string): string =>
  suiteId === "expert" ? "0.00" : "n/a";

export const defectsFor = (target: TargetId): Defect[] =>
  data.defects.filter((d) => d.target === target);

export const targetIds = Object.keys(data.targets) as TargetId[];

/* ── formatting ────────────────────────────────────────────── */

export const pct = (v: number): string => `${(v * 100).toFixed(1)}%`;

export type Band = "high" | "mid" | "low";

export const bandOf = (v: number, good = 0.75, fair = 0.4): Band =>
  v >= good ? "high" : v >= fair ? "mid" : "low";

export const figureClass = (v: number, good = 0.75, fair = 0.4): string =>
  ({ high: "is-caught", mid: "is-mid", low: "is-missed" })[bandOf(v, good, fair)];

export const meterClass = (v: number, good = 0.75, fair = 0.4): string =>
  ({ high: "", mid: "mid", low: "low" })[bandOf(v, good, fair)];

export const severityTag = (s: Severity): string =>
  ({ blocker: "tag tag-accent", major: "tag tag-outline", minor: "tag tag-neutral" })[s];

/* ── wheel geometry ────────────────────────────────────────── */

/** Ring bounds, innermost first. Rings run best-recall-first outward. */
export const RING_RADII: [number, number][] = [
  [86, 118],
  [124, 156],
  [162, 194],
  [200, 232],
];

export const WHEEL_VIEWBOX = 560;
const C = WHEEL_VIEWBOX / 2;

/** An annular sector path, in viewBox units. */
export function arcPath(
  r0: number,
  r1: number,
  a0: number,
  a1: number,
): string {
  const at = (r: number, a: number): [number, number] => [
    C + r * Math.cos(a),
    C + r * Math.sin(a),
  ];
  const [x0, y0] = at(r1, a0);
  const [x1, y1] = at(r1, a1);
  const [x2, y2] = at(r0, a1);
  const [x3, y3] = at(r0, a0);
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return [
    `M${x0.toFixed(2)} ${y0.toFixed(2)}`,
    `A${r1} ${r1} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`,
    `L${x2.toFixed(2)} ${y2.toFixed(2)}`,
    `A${r0} ${r0} 0 ${large} 0 ${x3.toFixed(2)} ${y3.toFixed(2)}`,
    "Z",
  ].join(" ");
}

export interface WheelCell {
  defectId: string;
  suiteId: string;
  hit: boolean;
  d: string;
  delayMs: number;
  tip: string;
}

export interface WheelSpoke {
  defectId: string;
  label: string;
  leftPct: string;
  topPct: string;
}

/** Everything the wheel needs, computed once on the server. */
export function buildWheel(staggerMs = 12): {
  cells: WheelCell[];
  spokes: WheelSpoke[];
} {
  const ranked = data.scores.map((s) => s.suite);
  const n = data.defects.length;
  const step = (Math.PI * 2) / n;
  const gap = step * 0.1;
  const cells: WheelCell[] = [];
  const spokes: WheelSpoke[] = [];

  data.defects.forEach((defect, di) => {
    const a0 = -Math.PI / 2 + di * step + gap / 2;
    const a1 = -Math.PI / 2 + (di + 1) * step - gap / 2;

    ranked.forEach((suiteId, ri) => {
      const hit = caught(defect.id, suiteId);
      const first = firstCheck(defect.id, suiteId);
      const suite = suiteById(suiteId);
      cells.push({
        defectId: defect.id,
        suiteId,
        hit,
        d: arcPath(RING_RADII[ri][0], RING_RADII[ri][1], a0, a1),
        delayMs: (di * ranked.length + ri) * staggerMs,
        tip: hit
          ? `${suite.name} caught ${defect.id}${first ? ` via ${first}` : ""}`
          : `${suite.name} missed ${defect.id}: ${defect.hint}`,
      });
    });

    const mid = -Math.PI / 2 + (di + 0.5) * step;
    const r = 252;
    spokes.push({
      defectId: defect.id,
      label: defect.id,
      leftPct: `${(((C + r * Math.cos(mid)) / WHEEL_VIEWBOX) * 100).toFixed(2)}%`,
      topPct: `${(((C + r * Math.sin(mid)) / WHEEL_VIEWBOX) * 100).toFixed(2)}%`,
    });
  });

  return { cells, spokes };
}

export const NAV = [
  { href: "/", label: "Overview" },
  { href: "/benchmark", label: "Benchmark" },
  { href: "/defects", label: "Defects" },
  { href: "/suites", label: "Suites" },
  { href: "/runs", label: "Runs" },
  { href: "/lab", label: "Lab" },
] as const;
