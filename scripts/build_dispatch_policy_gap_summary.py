from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


COMPARISONS = [
    ("warmup_vs_coldstart", "warmup", "coldstart"),
    ("best_heuristic_vs_coldstart", "heuristic_feasible_count", "coldstart"),
    ("warmup_vs_best_heuristic", "warmup", "heuristic_feasible_count"),
    ("oracle_vs_warmup", "oracle", "warmup"),
    ("oracle_vs_coldstart", "oracle", "coldstart"),
]


def _row_by_policy(df: pd.DataFrame, policy: str) -> pd.Series:
    rows = df[df["policy"] == policy]
    if rows.empty:
        raise ValueError(f"Missing policy row: {policy}")
    return rows.iloc[0]


def main() -> None:
    source = pd.read_csv(RESULTS / "dispatch_primary_ci_summary.csv")
    rows: list[dict[str, object]] = []
    for domain, domain_df in source.groupby("domain", sort=False):
        for comparison, better_policy, baseline_policy in COMPARISONS:
            better = _row_by_policy(domain_df, better_policy)
            baseline = _row_by_policy(domain_df, baseline_policy)
            delta = (
                float(better["profit_per_launched_driver_mean"])
                - float(baseline["profit_per_launched_driver_mean"])
            )
            conservative_low = (
                float(better["profit_per_launched_driver_ci_low"])
                - float(baseline["profit_per_launched_driver_ci_high"])
            )
            conservative_high = (
                float(better["profit_per_launched_driver_ci_high"])
                - float(baseline["profit_per_launched_driver_ci_low"])
            )
            rows.append(
                {
                    "domain": domain,
                    "scenario_name": better["scenario_name"],
                    "density_pct": int(better["density_pct"]),
                    "comparison": comparison,
                    "better_policy": better_policy,
                    "baseline_policy": baseline_policy,
                    "delta_profit_per_driver": delta,
                    "delta_ci_low_conservative": conservative_low,
                    "delta_ci_high_conservative": conservative_high,
                    "n_seeds": int(better["n_seeds"]),
                    "driver_sample_size": int(better["driver_sample_size"]),
                    "uncertainty_note": (
                        "Seed-level intervals are computed from dispatch summary artifacts. "
                        "They collapse here because fixed retained-rider samples make the simulator nearly deterministic; "
                        "raw driver-level dispatch outcomes are not bundled in this local package."
                    ),
                }
            )
    out = RESULTS / "dispatch_policy_gap_summary.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Wrote {out.relative_to(ROOT)} with {len(rows)} policy-gap rows")


if __name__ == "__main__":
    main()
