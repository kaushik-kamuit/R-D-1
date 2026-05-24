from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


POLICIES = {
    "coldstart": "coldstart_profit_per_driver",
    "heuristic_feasible_count": "best_heuristic_profit_per_driver",
    "warmup": "warmup_profit_per_driver",
    "oracle": "oracle_profit_per_driver",
}


def _policy_row(rows: pd.DataFrame, policy: str) -> pd.Series:
    matches = rows[rows["policy"] == policy]
    if matches.empty:
        raise ValueError(f"Missing policy {policy}")
    return matches.iloc[0]


def main() -> None:
    source = pd.read_csv(RESULTS / "dispatch_density_ci_summary.csv")
    rows: list[dict[str, object]] = []
    for (domain, density_pct), group in source.groupby(["domain", "density_pct"], sort=True):
        cold = _policy_row(group, "coldstart")
        heuristic = _policy_row(group, "heuristic_feasible_count")
        warmup = _policy_row(group, "warmup")
        oracle = _policy_row(group, "oracle")
        rows.append(
            {
                "domain": domain,
                "density_pct_of_retained_sample": int(density_pct),
                "approx_pct_of_full_rider_extract": float(density_pct) * 0.25,
                "driver_sample_size": int(warmup["driver_sample_size"]),
                "n_seeds": int(warmup["n_seeds"]),
                "coldstart_profit_per_driver": float(cold["profit_per_launched_driver_mean"]),
                "best_heuristic_profit_per_driver": float(heuristic["profit_per_launched_driver_mean"]),
                "warmup_profit_per_driver": float(warmup["profit_per_launched_driver_mean"]),
                "oracle_profit_per_driver": float(oracle["profit_per_launched_driver_mean"]),
                "best_heuristic_gain_vs_coldstart": (
                    float(heuristic["profit_per_launched_driver_mean"])
                    - float(cold["profit_per_launched_driver_mean"])
                ),
                "warmup_gain_vs_coldstart": (
                    float(warmup["profit_per_launched_driver_mean"])
                    - float(cold["profit_per_launched_driver_mean"])
                ),
                "oracle_gain_vs_coldstart": (
                    float(oracle["profit_per_launched_driver_mean"])
                    - float(cold["profit_per_launched_driver_mean"])
                ),
                "warmup_gain_vs_best_heuristic": (
                    float(warmup["profit_per_launched_driver_mean"])
                    - float(heuristic["profit_per_launched_driver_mean"])
                ),
                "interpretation_note": (
                    "Density varies the active fraction of the fixed 25% retained rider sample. "
                    "It is a retained-sample sensitivity check, not a replacement for rerunning raw extraction "
                    "with different pre-sampling probabilities."
                ),
            }
        )
    out = RESULTS / "retained_density_sensitivity.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Wrote {out.relative_to(ROOT)} with {len(rows)} density-sensitivity rows")


if __name__ == "__main__":
    main()
