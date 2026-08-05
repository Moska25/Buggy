import { data, figureClass, pct, suiteById } from "@/lib/data";

/** Which ring is which suite, in the wheel's own order. */
export default function RingLegend() {
  return (
    <div className="ring-legend">
      {data.scores.map((s) => (
        <div key={s.suite} className="ring">
          <span
            className={`ring-swatch ${figureClass(s.recall)}`}
            style={{
              background: `color-mix(in srgb, currentColor ${Math.round(
                s.recall * 100,
              )}%, transparent)`,
            }}
            aria-hidden
          />
          <span className="ring-name">{suiteById(s.suite).name}</span>
          <span className={`ring-pct num ${figureClass(s.recall)}`}>
            {pct(s.recall)}
          </span>
        </div>
      ))}
    </div>
  );
}
