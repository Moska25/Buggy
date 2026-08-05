"use client";

import { useState } from "react";

/**
 * Wheel for reading the shape of the run, grid for reading exact rows.
 * Both views are rendered on the server and handed in as nodes; this component
 * only owns which one is on screen.
 */
export default function BoardSwitch({
  wheel,
  grid,
  initial = "wheel",
}: {
  wheel: React.ReactNode;
  grid: React.ReactNode;
  initial?: "wheel" | "grid";
}) {
  const [view, setView] = useState<"wheel" | "grid">(initial);

  return (
    <>
      <div
        className="row"
        style={{ alignItems: "flex-end", marginBottom: 22, gap: 16 }}
      >
        <div style={{ flex: "1 1 320px" }}>
          <h2 className="h-section" style={{ marginBottom: 6 }}>
            The board
          </h2>
          <p className="muted" style={{ margin: 0 }}>
            17 defects against 4 suites. Filled means caught; hollow means it
            walked past.
          </p>
        </div>
        <div className="switch" role="group" aria-label="Board view">
          <button
            type="button"
            aria-pressed={view === "wheel"}
            onClick={() => setView("wheel")}
          >
            Wheel
          </button>
          <button
            type="button"
            aria-pressed={view === "grid"}
            onClick={() => setView("grid")}
          >
            Grid
          </button>
        </div>
      </div>

      {view === "wheel" ? (
        <div className="panel panel-lg">
          <div className="wheel">{wheel}</div>
        </div>
      ) : (
        grid
      )}

      <div
        className="row muted"
        style={{ gap: 22, marginTop: 20, fontSize: 13.5 }}
      >
        <span className="row" style={{ gap: 9 }}>
          <span className="pip-sm" aria-hidden />
          caught: failed on the broken build, passed on the clean one
        </span>
        <span className="row" style={{ gap: 9 }}>
          <span className="pip-sm miss" aria-hidden />
          missed: the defect survived this suite
        </span>
      </div>
    </>
  );
}
