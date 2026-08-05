"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  WHEEL_VIEWBOX,
  catchCount,
  defectById,
  type WheelCell,
  type WheelSpoke,
} from "@/lib/data";

/**
 * The catch wheel. Seventeen spokes (defects) by four rings (suites, best
 * recall first from the centre out). A filled arc is a detection earned under
 * the benchmark's rule; a hollow dashed arc is a defect that walked past.
 *
 * Geometry is computed on the server (lib/data.ts buildWheel) — this component
 * only owns hover and navigation.
 */
export default function CatchWheel({
  cells,
  spokes,
  linkThrough = false,
}: {
  cells: WheelCell[];
  spokes: WheelSpoke[];
  linkThrough?: boolean;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const router = useRouter();

  const hovered = hover ? defectById(hover) : undefined;
  const hub = hovered ? hovered.id : "17 × 4";
  const caption = hovered
    ? `${hovered.title} — caught by ${catchCount(hovered.id)} of 4`
    : "Hover a spoke to read its defect";

  return (
    <div>
      <div className="wheel-box" data-hover={hover ?? undefined}>
        <svg viewBox={`0 0 ${WHEEL_VIEWBOX} ${WHEEL_VIEWBOX}`} role="img"
             aria-label="Detection wheel: 17 defects by 4 test suites">
          {cells.map((cell) => (
            <path
              key={`${cell.defectId}-${cell.suiteId}`}
              d={cell.d}
              className={[
                "arc",
                cell.hit ? "arc-hit" : "arc-miss",
                hover === cell.defectId ? "on" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              style={{ animationDelay: `${cell.delayMs}ms` }}
              onMouseEnter={() => setHover(cell.defectId)}
              onMouseLeave={() => setHover(null)}
              onClick={
                linkThrough
                  ? () => router.push(`/defects/${cell.defectId}`)
                  : undefined
              }
            >
              <title>{cell.tip}</title>
            </path>
          ))}
        </svg>

        <div className="spokes">
          {spokes.map((s) => (
            <span
              key={s.defectId}
              className={hover === s.defectId ? "on" : undefined}
              style={{ left: s.leftPct, top: s.topPct }}
            >
              {s.label}
            </span>
          ))}
        </div>

        <div className="hub num">{hub}</div>
      </div>

      <p className="wheel-caption" aria-live="polite">
        {caption}
      </p>
    </div>
  );
}
