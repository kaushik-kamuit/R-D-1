from __future__ import annotations

import argparse
import sys
from pathlib import Path

import h3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_prep.domain_config import get_domain_config
from dispatch import DispatchConfig, RollingDispatcher
from matching.rider_index import RiderIndex
from simulation.domain_io import load_domain_assets, load_h3_stats_dict
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


class ZeroPredictor:
    """Predictor stub; this diagnostic reports heuristic/oracle corridor effects."""

    def rank_routes(self, feature_rows: list[dict[str, float]]) -> list[tuple[int, float]]:
        return [(idx, 0.0) for idx, _row in enumerate(feature_rows)]


VARIANTS = [
    {
        "tag": "primary_h3r9_k1_d80",
        "h3_resolution": 9,
        "corridor_k_ring": 1,
        "corridor_densify_step_m": 80.0,
        "note": "Primary manuscript corridor setting.",
    },
    {
        "tag": "coarse_h3r8_k1_d80",
        "h3_resolution": 8,
        "corridor_k_ring": 1,
        "corridor_densify_step_m": 80.0,
        "note": "Coarser cells test whether corridor precision matters.",
    },
    {
        "tag": "wide_h3r9_k2_d80",
        "h3_resolution": 9,
        "corridor_k_ring": 2,
        "corridor_densify_step_m": 80.0,
        "note": "Wider corridor tests candidate-pool expansion.",
    },
    {
        "tag": "sparse_h3r9_k1_d160",
        "h3_resolution": 9,
        "corridor_k_ring": 1,
        "corridor_densify_step_m": 160.0,
        "note": "Less dense route sampling tests densification sensitivity.",
    },
]


def _summarize(rows: list[dict[str, object]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    group_cols = [
        "sensitivity_tag",
        "policy",
        "h3_resolution",
        "corridor_k_ring",
        "corridor_densify_step_m",
        "diagnostic_note",
        "domain",
        "density_pct",
        "matching_window_min",
        "max_detour_min",
        "batch_seconds",
        "scenario_name",
        "driver_sample_size",
        "n_seeds",
    ]
    metric_cols = [
        "launched_drivers",
        "total_profit",
        "profit_per_launched_driver",
        "served_riders",
        "rider_service_rate",
        "mean_wait_min",
        "mean_matched_riders_per_driver",
        "seat_occupancy",
        "mean_detour_min",
        "mean_eval_time_s",
        "mean_batch_runtime_s",
    ]
    return df.groupby(group_cols, dropna=False, as_index=False)[metric_cols].mean()


def _prepare_variant_pool(
    dispatcher: RollingDispatcher,
    riders_df: pd.DataFrame,
    *,
    h3_resolution: int,
) -> tuple[pd.DataFrame, RiderIndex, dict, dict]:
    sampled = dispatcher._sample_density(riders_df)
    if h3_resolution != 9:
        sampled = sampled.copy()
        sampled["pickup_h3"] = [
            h3.latlng_to_cell(float(lat), float(lng), h3_resolution)
            for lat, lng in zip(sampled["pickup_lat"], sampled["pickup_lng"])
        ]
        sampled["dropoff_h3"] = [
            h3.latlng_to_cell(float(lat), float(lng), h3_resolution)
            for lat, lng in zip(sampled["dropoff_lat"], sampled["dropoff_lng"])
        ]
    rider_index = RiderIndex(sampled, index_bin_minutes=dispatcher.config.index_bin_minutes)
    request_states = dispatcher._prepare_request_states(sampled)
    request_batches = dispatcher._group_requests_by_batch(sampled)
    return sampled, rider_index, request_states, request_batches


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a cached dispatch-level H3/corridor sensitivity diagnostic."
    )
    parser.add_argument("--sample", type=int, default=100)
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--fetch", action="store_true", help="Allow OSRM fetches for cache misses.")
    args = parser.parse_args()

    policies = ["coldstart", "heuristic_feasible_count", "oracle"]
    seeds = [42, 43, 44, 45, 46][: args.seeds]
    domain_config, drivers_df, riders_df = load_domain_assets(
        "yellow",
        driver_columns=DRIVER_COLS,
        rider_columns=RIDER_COLS,
        split="test",
    )
    if args.sample < len(drivers_df):
        drivers_df = drivers_df.sample(n=args.sample, random_state=42).reset_index(drop=True)
    riders_df = riders_df.reset_index(drop=True)
    h3_stats = load_h3_stats_dict(domain_config)

    rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        router = OSRMRouter(
            cache_path=get_domain_config("yellow").route_cache_path,
            cache_only=not args.fetch,
        )
        config = DispatchConfig(
            domain="yellow",
            scenario_name=f"dispatch_corridor_{variant['tag']}",
            density_pct=10,
            max_request_offset_min=5,
            max_detour_min=4.0,
            h3_resolution=int(variant["h3_resolution"]),
            corridor_k_ring=int(variant["corridor_k_ring"]),
            corridor_densify_step_m=float(variant["corridor_densify_step_m"]),
        )
        dispatcher = RollingDispatcher(
            config,
            domain_config=domain_config,
            router=router,
            predictor=ZeroPredictor(),
            h3_stats_dict=h3_stats,
        )
        sampled_riders, rider_index, request_states, request_batches = _prepare_variant_pool(
            dispatcher,
            riders_df,
            h3_resolution=int(variant["h3_resolution"]),
        )
        for policy in policies:
            for seed in seeds:
                _outcomes, batch_metrics, summary = dispatcher.run_policy(
                    policy,
                    drivers_df,
                    riders_df,
                    seed=seed,
                    sampled_riders_df=sampled_riders,
                    rider_index=rider_index,
                    request_states=request_states,
                    request_batches=request_batches,
                )
                summary_row = summary.to_dict()
                summary_row["mean_batch_runtime_s"] = (
                    sum(row.runtime_s for row in batch_metrics) / max(len(batch_metrics), 1)
                )
                rows.append(
                    {
                        **summary_row,
                        "domain": "yellow",
                        "density_pct": config.density_pct,
                        "matching_window_min": config.max_request_offset_min,
                        "max_detour_min": config.max_detour_min,
                        "batch_seconds": config.batch_seconds,
                        "scenario_name": config.scenario_name,
                        "driver_sample_size": len(drivers_df),
                        "n_seeds": len(seeds),
                        "sensitivity_tag": variant["tag"],
                        "h3_resolution": variant["h3_resolution"],
                        "corridor_k_ring": variant["corridor_k_ring"],
                        "corridor_densify_step_m": variant["corridor_densify_step_m"],
                        "diagnostic_note": variant["note"],
                    }
                )
        router.flush_cache()

    output = RESULTS / "dispatch_corridor_sensitivity.csv"
    _summarize(rows).to_csv(output, index=False)
    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
