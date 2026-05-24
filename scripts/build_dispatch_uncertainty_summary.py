from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

INPUTS = [
    ("primary_yellow_green", RESULTS / "domain_transfer_ci_summary.csv"),
    ("yellow_density_sweep", RESULTS / "dispatch_density_ci_summary.csv"),
]

METRICS = [
    "profit_per_launched_driver",
    "served_riders",
    "rider_service_rate",
    "mean_wait_min",
    "mean_matched_riders_per_driver",
    "mean_eval_time_s",
    "mean_batch_runtime_s",
]


def _domain_for(source: str, row: pd.Series) -> str:
    if "domain" in row and pd.notna(row["domain"]):
        return str(row["domain"])
    if source == "yellow_density_sweep":
        return "yellow"
    return "unknown"


def main() -> None:
    rows: list[dict[str, object]] = []
    for source, path in INPUTS:
        if not path.exists():
            raise SystemExit(f"Missing required dispatch CI input: {path.relative_to(ROOT)}")
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            for metric in METRICS:
                mean_col = f"{metric}_mean"
                low_col = f"{metric}_ci_low"
                high_col = f"{metric}_ci_high"
                if not {mean_col, low_col, high_col}.issubset(df.columns):
                    continue
                low = float(row[low_col])
                high = float(row[high_col])
                width = high - low
                rows.append(
                    {
                        "source": source,
                        "domain": _domain_for(source, row),
                        "scenario_name": row.get("scenario_name", ""),
                        "density_pct": row.get("density_pct", ""),
                        "policy": row.get("policy", ""),
                        "metric": metric,
                        "mean": float(row[mean_col]),
                        "ci_low": low,
                        "ci_high": high,
                        "ci_width": width,
                        "interval_collapsed": abs(width) <= 1e-12,
                        "n_seeds": int(row.get("n_seeds", 0)),
                    }
                )

    out = RESULTS / "dispatch_uncertainty_summary.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    noncollapsed = sum(not bool(row["interval_collapsed"]) for row in rows)
    print(
        f"Wrote {out.relative_to(ROOT)} with {len(rows)} metric rows; "
        f"non-collapsed intervals={noncollapsed}"
    )


if __name__ == "__main__":
    main()
