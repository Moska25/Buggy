import Link from "next/link";
import { caught, data, firstCheck, suiteById } from "@/lib/data";

/** The tabular reading of the same board — for scanning, sorting by eye. */
export default function BoardGrid() {
  return (
    <div className="tablewrap">
      <table className="table" style={{ minWidth: 720 }}>
        <thead>
          <tr>
            <th style={{ width: "40%" }}>Defect</th>
            {data.suiteOrder.map((sid) => (
              <th key={sid} className="center">
                {suiteById(sid).name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.defects.map((d) => (
            <tr key={d.id}>
              <td>
                <Link
                  href={`/defects/${d.id}`}
                  style={{ fontFamily: "var(--font-heading)", fontSize: 15 }}
                >
                  {d.id}
                </Link>
                <span
                  style={{
                    fontSize: 11,
                    marginLeft: 8,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                    color: "var(--color-accent-700)",
                  }}
                >
                  {d.category}
                </span>
                <div className="muted" style={{ fontSize: 13 }}>
                  {d.title}
                </div>
              </td>
              {data.suiteOrder.map((sid) => {
                const hit = caught(d.id, sid);
                const first = firstCheck(d.id, sid);
                const suite = suiteById(sid);
                return (
                  <td key={sid} className="center">
                    <span
                      className={`pip${hit ? "" : " miss"}`}
                      title={
                        hit
                          ? `${suite.name} caught ${d.id}${first ? ` via ${first}` : ""}`
                          : `${suite.name} missed ${d.id}: ${d.hint}`
                      }
                    >
                      {hit ? "✓" : "·"}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
