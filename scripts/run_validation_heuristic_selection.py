from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_prep.domain_config import get_domain_config
from matching.rider_index import RiderIndex
from simulation.domain_io import build_driver_trips, load_h3_stats_dict
from simulation.route_evaluator import evaluate_driver_policies
from spatial.router import OSRMRouter

RESULTS = ROOT / "results"

DRIVER_COLS = [
    "split",
    "pickup_datetime",
    "origin_lat",
    "origin_lng",
    "dest_lat",
    "dest_lng",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "trip_distance_miles",
]
RIDER_COLS = [
    "split",
    "pickup_datetime",
    "pickup_h3",
    "dropoff_h3",
    "pickup_lat",
    "pickup_lng",
    "dropoff_lat",
    "dropoff_lng",
    "passenger_count",
    "fare_amount",
]
HEURISTICS = [
    "heuristic_count",
    "heuristic_path_buffer",
    "heuristic_fare_density",
    "heuristic_feasible_count",
    "heuristic_profit_proxy",
]


class ZeroPredictor:
    def rank_routes(self, feature_rows: list[dict[str, float]]) -> list[tuple[int, float]]:
        return [(idx, 0.0) for idx, _row in enumerate(feature_rows)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Select strongest non-ML heuristic on a March validation probe.")
    parser.add_argument("--sample", type=int, default=30)
    parser.add_argument("--density-pct", type=int, default=10)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--cache-only", action="store_true", help="Do not fetch missing March routes from OSRM.")
    args = parser.parse_args()

    config = get_domain_config("yellow")
    drivers = pd.read_parquet(config.drivers_path(), columns=DRIVER_COLS)
    riders = pd.read_parquet(config.riders_path(), columns=RIDER_COLS)
    drivers = drivers.loc[
        (drivers["split"] == "train") & (drivers["pickup_datetime"].dt.month == 3)
    ].reset_index(drop=True)
    riders = riders.loc[
        (riders["split"] == "train") & (riders["pickup_datetime"].dt.month == 3)
    ].reset_index(drop=True)
    if args.density_pct < 100:
        riders = riders.sample(frac=args.density_pct / 100.0, random_state=args.seed).reset_index(drop=True)
    drivers = drivers.sample(n=min(args.sample * 5, len(drivers)), random_state=args.seed).reset_index(drop=True)

    rider_index = RiderIndex(riders, index_bin_minutes=15)
    h3_stats = load_h3_stats_dict(config)
    validation_cache = ROOT / "data" / "route_cache_validation_yellow.db"
    router = OSRMRouter(cache_path=validation_cache, cache_only=args.cache_only)
    predictor = ZeroPredictor()

    rows = []
    evaluated = 0
    trips = build_driver_trips(
        drivers,
        seats=3,
        max_detour_min=4,
        platform_share=0.50,
        cost_per_mile=0.67,
        urban_speed_kmh=40,
    )
    for frame_idx, trip in enumerate(trips):
        routes = router.get_alternative_routes(trip.origin, trip.destination, max_alternatives=3)
        if len(routes) < 2:
            continue
        row = drivers.iloc[frame_idx]
        evaluation = evaluate_driver_policies(
            trip,
            rider_index,
            predictor,
            h3_stats,
            day_of_week=int(row["day_of_week"]),
            is_weekend=int(row["is_weekend"]),
            day_of_month=int(pd.Timestamp(row["pickup_datetime"]).day),
            seed=args.seed,
            candidate_window_bins=1,
            max_request_offset_min=5,
            h3_resolution=9,
            corridor_k_ring=1,
            corridor_densify_step_m=80.0,
            routes=routes,
        )
        for heuristic in HEURISTICS:
            plan = evaluation.plans[heuristic]
            rows.append(
                {
                    "driver_id": evaluated,
                    "heuristic": heuristic,
                    "profit": plan.outcome.profit,
                    "matched_riders": plan.outcome.matched_riders,
                    "route_idx": plan.route_idx,
                }
            )
        evaluated += 1
        if evaluated >= args.sample:
            break
    router.flush_cache()

    if not rows:
        raise RuntimeError("No March validation drivers with at least two routes were evaluated.")
    raw = pd.DataFrame(rows)
    summary = raw.groupby("heuristic", as_index=False).agg(
        mean_profit=("profit", "mean"),
        mean_matched_riders=("matched_riders", "mean"),
        drivers_evaluated=("driver_id", "nunique"),
    )
    summary["rank_by_validation_profit"] = summary["mean_profit"].rank(method="first", ascending=False).astype(int)
    summary["selected_on_validation"] = summary["rank_by_validation_profit"].eq(1)
    summary["sample_scope"] = "march_yellow_validation_probe"
    summary["density_pct"] = args.density_pct
    summary["seed"] = args.seed
    summary["note"] = "Validation probe used to pre-select the non-ML heuristic before April test interpretation."
    raw.to_csv(RESULTS / "validation_heuristic_selection_raw.csv", index=False)
    summary.sort_values("rank_by_validation_profit").to_csv(RESULTS / "validation_heuristic_selection.csv", index=False)
    print(summary.sort_values("rank_by_validation_profit").to_string(index=False))


if __name__ == "__main__":
    main()
