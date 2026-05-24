from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_prep.domain_config import get_domain_config
from matching.matcher import METERS_PER_MILE
from matching.rider_index import RiderIndex
from simulation.domain_io import build_driver_trips, load_h3_stats_dict
from simulation.route_evaluator import DriverPolicyEvaluation, RouteEvaluation, evaluate_driver_policies
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
    """Predictor stub for non-ML baseline probes."""

    def rank_routes(self, feature_rows: list[dict[str, float]]) -> list[tuple[int, float]]:
        return [(idx, 0.0) for idx, _row in enumerate(feature_rows)]


@dataclass(frozen=True)
class SelectedDriver:
    frame_idx: int
    trip_idx: int
    timestamp: pd.Timestamp


def _select_cached_multiroute_drivers(
    drivers: pd.DataFrame,
    router: OSRMRouter,
    *,
    sample: int,
) -> list[SelectedDriver]:
    trips = build_driver_trips(
        drivers,
        seats=3,
        max_detour_min=4,
        platform_share=0.50,
        cost_per_mile=0.67,
        urban_speed_kmh=40,
    )
    selected: list[SelectedDriver] = []
    for idx, trip in enumerate(trips):
        routes = router.get_alternative_routes(trip.origin, trip.destination, max_alternatives=3)
        if len(routes) > 1:
            selected.append(
                SelectedDriver(
                    frame_idx=idx,
                    trip_idx=trip.driver_id,
                    timestamp=pd.Timestamp(trip.departure_time),
                )
            )
            if len(selected) >= sample:
                break
    return selected


def _available_ids(
    rider_times: pd.Series,
    unserved: set[int],
    query_time: pd.Timestamp,
    request_window_min: int,
) -> set[int]:
    if not unserved:
        return set()
    idx = np.fromiter(unserved, dtype=np.int64)
    times = rider_times.iloc[idx]
    mask = (times <= query_time) & (query_time <= times + pd.Timedelta(minutes=request_window_min))
    return set(idx[mask.to_numpy()].tolist())


def _profit(route_eval: RouteEvaluation, matched: list[dict] | None = None) -> float:
    if matched is None:
        return route_eval.actual_profit
    revenue = sum(row["fare_share"] for row in matched)
    cost = (route_eval.route.distance_m / METERS_PER_MILE) * 0.67
    return float(revenue - cost)


def _nearest_route_idx(route_evals: tuple[RouteEvaluation, ...]) -> int:
    best_idx = 0
    best_key = (float("inf"), 0)
    for route_eval in route_evals:
        if route_eval.feasible:
            mean_detour = float(np.mean([row["detour_minutes"] for row in route_eval.feasible]))
            key = (mean_detour, route_eval.route_idx)
        else:
            key = (float("inf"), route_eval.route_idx)
        if key < best_key:
            best_key = key
            best_idx = route_eval.route_idx
    return best_idx


def _evaluate_driver(
    trip,
    row: pd.Series,
    routes,
    rider_index: RiderIndex,
    h3_stats: dict[str, dict],
    available: set[int],
    seed: int,
) -> DriverPolicyEvaluation:
    return evaluate_driver_policies(
        trip,
        rider_index,
        ZeroPredictor(),
        h3_stats,
        day_of_week=int(row["day_of_week"]),
        is_weekend=int(row["is_weekend"]),
        day_of_month=int(pd.Timestamp(row["pickup_datetime"]).day),
        seed=seed,
        candidate_window_bins=1,
        max_request_offset_min=5,
        h3_resolution=9,
        corridor_k_ring=1,
        corridor_densify_step_m=80.0,
        available_rider_ids=available,
        routes=routes,
    )


def _sequential_nearest_route(
    selected: list[SelectedDriver],
    drivers: pd.DataFrame,
    rider_index: RiderIndex,
    rider_times: pd.Series,
    router: OSRMRouter,
    h3_stats: dict[str, dict],
    *,
    seed: int,
) -> dict[str, float]:
    trips = build_driver_trips(
        drivers.iloc[[row.frame_idx for row in selected]].reset_index(drop=True),
        seats=3,
        max_detour_min=4,
        platform_share=0.50,
        cost_per_mile=0.67,
        urban_speed_kmh=40,
    )
    unserved = set(range(len(rider_index.riders)))
    profits: list[float] = []
    matched_counts: list[int] = []
    for selected_row, trip, (_, driver_row) in zip(
        sorted(selected, key=lambda row: row.timestamp),
        trips,
        drivers.iloc[[row.frame_idx for row in selected]].reset_index(drop=True).iterrows(),
    ):
        available = _available_ids(rider_times, unserved, selected_row.timestamp, 5)
        routes = router.get_alternative_routes(trip.origin, trip.destination, max_alternatives=3)
        evaluation = _evaluate_driver(trip, driver_row, routes, rider_index, h3_stats, available, seed)
        if not evaluation.route_evaluations:
            continue
        route_eval = evaluation.route_evaluations[_nearest_route_idx(evaluation.route_evaluations)]
        matched = [row for row in route_eval.matched if row["rider_idx"] in available]
        profits.append(_profit(route_eval, matched))
        matched_counts.append(len(matched))
        unserved.difference_update(row["rider_idx"] for row in matched)
    return {
        "baseline": "greedy_nearest_route_dispatch",
        "drivers_evaluated": len(profits),
        "profit_per_driver": float(np.mean(profits)) if profits else 0.0,
        "matched_riders_per_driver": float(np.mean(matched_counts)) if matched_counts else 0.0,
        "served_riders": int(sum(matched_counts)),
    }


def _batch_bipartite_single_rider(
    selected: list[SelectedDriver],
    drivers: pd.DataFrame,
    rider_index: RiderIndex,
    rider_times: pd.Series,
    router: OSRMRouter,
    h3_stats: dict[str, dict],
    *,
    seed: int,
) -> dict[str, float]:
    selected_df = drivers.iloc[[row.frame_idx for row in selected]].reset_index(drop=True)
    trips = build_driver_trips(
        selected_df,
        seats=3,
        max_detour_min=4,
        platform_share=0.50,
        cost_per_mile=0.67,
        urban_speed_kmh=40,
    )
    graph = nx.Graph()
    driver_costs: dict[int, float] = {}
    edge_payload: dict[tuple[str, str], tuple[RouteEvaluation, dict]] = {}
    for local_idx, (selected_row, trip, (_, driver_row)) in enumerate(zip(selected, trips, selected_df.iterrows())):
        routes = router.get_alternative_routes(trip.origin, trip.destination, max_alternatives=3)
        if not routes:
            continue
        driver_node = f"d:{local_idx}"
        graph.add_node(driver_node, bipartite=0)
        driver_costs[local_idx] = (routes[0].distance_m / METERS_PER_MILE) * 0.67
        available = _available_ids(rider_times, set(range(len(rider_index.riders))), selected_row.timestamp, 5)
        evaluation = _evaluate_driver(trip, driver_row, routes, rider_index, h3_stats, available, seed)
        best_by_rider: dict[int, tuple[float, RouteEvaluation, dict]] = {}
        for route_eval in evaluation.route_evaluations:
            route_cost = (route_eval.route.distance_m / METERS_PER_MILE) * 0.67
            for feasible in route_eval.feasible:
                rider_id = int(feasible["rider_idx"])
                weight = float(feasible["fare_share"] - route_cost)
                if rider_id not in best_by_rider or weight > best_by_rider[rider_id][0]:
                    best_by_rider[rider_id] = (weight, route_eval, feasible)
        for rider_id, (weight, route_eval, feasible) in best_by_rider.items():
            rider_node = f"r:{rider_id}"
            graph.add_node(rider_node, bipartite=1)
            graph.add_edge(driver_node, rider_node, weight=weight)
            edge_payload[(driver_node, rider_node)] = (route_eval, feasible)
            edge_payload[(rider_node, driver_node)] = (route_eval, feasible)

    matching = nx.algorithms.matching.max_weight_matching(graph, maxcardinality=False, weight="weight")
    matched_driver_ids: set[int] = set()
    profits: list[float] = []
    for left, right in matching:
        if left.startswith("r:"):
            left, right = right, left
        if not left.startswith("d:"):
            continue
        driver_idx = int(left.split(":", 1)[1])
        route_eval, feasible = edge_payload[(left, right)]
        profits.append(_profit(route_eval, [feasible]))
        matched_driver_ids.add(driver_idx)
    for driver_idx, cost in driver_costs.items():
        if driver_idx not in matched_driver_ids:
            profits.append(-cost)
    return {
        "baseline": "batch_bipartite_single_rider",
        "drivers_evaluated": len(driver_costs),
        "profit_per_driver": float(np.mean(profits)) if profits else 0.0,
        "matched_riders_per_driver": len(matched_driver_ids) / max(len(driver_costs), 1),
        "served_riders": len(matched_driver_ids),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run stronger cached-subset dispatch baselines requested by reviewers.")
    parser.add_argument("--sample", type=int, default=100)
    parser.add_argument("--density-pct", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    config = get_domain_config("yellow")
    drivers = pd.read_parquet(config.drivers_path(), columns=DRIVER_COLS)
    drivers = drivers.loc[drivers["split"] == "test"].reset_index(drop=True)
    riders = pd.read_parquet(config.riders_path(), columns=RIDER_COLS)
    riders = riders.loc[riders["split"] == "test"].reset_index(drop=True)
    if args.density_pct < 100:
        riders = riders.sample(frac=args.density_pct / 100.0, random_state=args.seed).reset_index(drop=True)

    router = OSRMRouter(cache_path=config.route_cache_path, cache_only=True)
    selected = _select_cached_multiroute_drivers(drivers, router, sample=args.sample)
    selected = sorted(selected, key=lambda row: row.timestamp)
    selected_drivers = drivers.iloc[[row.frame_idx for row in selected]].reset_index(drop=True)
    print(f"Selected {len(selected)} cached multi-route drivers from {len(drivers):,} April test drivers.")

    rider_index = RiderIndex(riders, index_bin_minutes=15)
    rider_times = rider_index.riders["pickup_datetime"]
    h3_stats = load_h3_stats_dict(config)

    rows = [
        _sequential_nearest_route(selected, drivers, rider_index, rider_times, router, h3_stats, seed=args.seed),
        _batch_bipartite_single_rider(selected, drivers, rider_index, rider_times, router, h3_stats, seed=args.seed),
    ]
    for row in rows:
        row["sample_scope"] = "cached_multiroute_april_yellow"
        row["density_pct"] = args.density_pct
        row["seed"] = args.seed
        row["driver_sample_size"] = len(selected_drivers)
        row["note"] = "Reviewer diagnostic baseline on cached multi-route subset; not a full production RTV solver."

    out = RESULTS / "stronger_dispatch_baselines.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
