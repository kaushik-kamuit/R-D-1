from __future__ import annotations

import argparse
import itertools
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_prep.domain_config import get_domain_config
from matching.matcher import METERS_PER_MILE, match_riders
from matching.rider_index import RiderIndex
from models.predict import FEATURE_COLS
from simulation.domain_io import build_driver_trips
from spatial.corridor import build_corridor
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
    "trip_distance_miles",
]

FEATURE_DESCRIPTIONS = {
    "route_distance_m": ("OSRM route distance in meters.", "OSRM route", "dispatch time", "per route", "No"),
    "route_duration_s": ("OSRM route duration in seconds.", "OSRM route", "dispatch time", "per route", "No"),
    "corridor_cell_count": ("Number of H3 cells in the expanded route corridor.", "corridor builder", "dispatch time", "per route", "No"),
    "hour_of_day": ("Driver departure hour.", "driver request", "dispatch time", "instantaneous", "No"),
    "day_of_week": ("Driver departure weekday index.", "driver request", "dispatch time", "instantaneous", "No"),
    "is_weekend": ("Weekend indicator.", "driver request", "dispatch time", "instantaneous", "No"),
    "corridor_rider_count": ("Exact-window riders retrieved in the route corridor.", "rider index", "dispatch time", "open requests", "No"),
    "corridor_demand_density": ("Exact-window rider count divided by corridor cell count.", "rider index", "dispatch time", "open requests", "No"),
    "mean_rider_fare": ("Mean fare among exact-window corridor candidates.", "rider index", "dispatch time", "open requests", "No"),
    "corridor_fare_density": ("Candidate fare sum divided by corridor cell count.", "rider index", "dispatch time", "open requests", "No"),
    "day_of_month": ("Calendar day of the month.", "driver request", "dispatch time", "instantaneous", "No"),
    "time_bin_15min": ("Quarter-hour departure bin.", "driver request", "dispatch time", "instantaneous", "No"),
    "hour_sin": ("Cyclic sine encoding of departure hour.", "driver request", "dispatch time", "instantaneous", "No"),
    "hour_cos": ("Cyclic cosine encoding of departure hour.", "driver request", "dispatch time", "instantaneous", "No"),
    "route_sinuosity": ("Route distance divided by straight-line OD distance.", "OSRM route", "dispatch time", "per route", "No"),
    "route_avg_speed_ms": ("Route distance divided by OSRM duration.", "OSRM route", "dispatch time", "per route", "No"),
    "bearing_sin": ("Cyclic sine encoding of OD bearing.", "driver OD", "dispatch time", "per route", "No"),
    "bearing_cos": ("Cyclic cosine encoding of OD bearing.", "driver OD", "dispatch time", "per route", "No"),
    "straight_line_dist_m": ("Haversine distance between driver origin and destination.", "driver OD", "dispatch time", "per route", "No"),
    "origin_landmark_dist_km": ("Minimum distance from origin to named NYC landmarks.", "driver OD", "dispatch time", "static", "No"),
    "dest_landmark_dist_km": ("Minimum distance from destination to named NYC landmarks.", "driver OD", "dispatch time", "static", "No"),
    "origin_jfk_km": ("Origin distance to JFK airport.", "driver OD", "dispatch time", "static", "No"),
    "origin_lga_km": ("Origin distance to LGA airport.", "driver OD", "dispatch time", "static", "No"),
    "origin_penn_km": ("Origin distance to Penn Station.", "driver OD", "dispatch time", "static", "No"),
    "origin_times_sq_km": ("Origin distance to Times Square.", "driver OD", "dispatch time", "static", "No"),
    "dest_jfk_km": ("Destination distance to JFK airport.", "driver OD", "dispatch time", "static", "No"),
    "dest_lga_km": ("Destination distance to LGA airport.", "driver OD", "dispatch time", "static", "No"),
    "dest_penn_km": ("Destination distance to Penn Station.", "driver OD", "dispatch time", "static", "No"),
    "dest_times_sq_km": ("Destination distance to Times Square.", "driver OD", "dispatch time", "static", "No"),
    "corridor_hist_pickups": ("Historical pickup count in route corridor.", "training history", "precomputed before evaluation month", "Jan-Mar history", "No"),
    "corridor_hist_dropoffs": ("Historical drop-off count in route corridor.", "training history", "precomputed before evaluation month", "Jan-Mar history", "No"),
    "corridor_hist_pickup_density": ("Historical pickup density in route corridor.", "training history", "precomputed before evaluation month", "Jan-Mar history", "No"),
    "corridor_hist_dropoff_density": ("Historical drop-off density in route corridor.", "training history", "precomputed before evaluation month", "Jan-Mar history", "No"),
    "corridor_hist_mean_fare": ("Historical mean fare in route corridor.", "training history", "precomputed before evaluation month", "Jan-Mar history", "No"),
    "corridor_hist_fare_density": ("Historical fare density in route corridor.", "training history", "precomputed before evaluation month", "Jan-Mar history", "No"),
    "origin_cell_pickups": ("Historical pickup count in origin H3 cell.", "training history", "precomputed before evaluation month", "Jan-Mar history", "No"),
    "origin_cell_mean_fare": ("Historical mean fare in origin H3 cell.", "training history", "precomputed before evaluation month", "Jan-Mar history", "No"),
    "dest_cell_dropoffs": ("Historical drop-off count in destination H3 cell.", "training history", "precomputed before evaluation month", "Jan-Mar history", "No"),
}


def _feature_family(feature: str) -> str:
    if feature in {
        "route_distance_m",
        "route_duration_s",
        "corridor_cell_count",
        "route_sinuosity",
        "route_avg_speed_ms",
        "bearing_sin",
        "bearing_cos",
        "straight_line_dist_m",
    }:
        return "Route geometry"
    if feature in {
        "hour_of_day",
        "day_of_week",
        "is_weekend",
        "day_of_month",
        "time_bin_15min",
        "hour_sin",
        "hour_cos",
    }:
        return "Temporal context"
    if feature in {
        "corridor_rider_count",
        "corridor_demand_density",
        "mean_rider_fare",
        "corridor_fare_density",
    }:
        return "Online corridor demand"
    if feature.startswith("corridor_hist_") or feature in {
        "origin_cell_pickups",
        "origin_cell_mean_fare",
        "dest_cell_dropoffs",
    }:
        return "Historical spatial demand"
    return "Landmark/cell context"


def _write_feature_dictionary() -> None:
    rows = []
    for feature in FEATURE_COLS:
        description, source, availability, window, leakage = FEATURE_DESCRIPTIONS[feature]
        rows.append({
            "feature_family": _feature_family(feature),
            "feature": feature,
            "definition": description,
            "source": source,
            "time_of_availability": availability,
            "aggregation_window": window,
            "uses_realized_test_outcome": leakage,
        })
    pd.DataFrame(rows).to_csv(RESULTS / "reviewer_feature_dictionary.csv", index=False)


def _write_external_dataset_audit() -> None:
    rows = [
        {
            "candidate": "Chicago Transportation Network Providers / Taxi",
            "source_url": "https://data.cityofchicago.org/Transportation/Transportation-Network-Providers-Trips-2020/rmc8-eqv4",
            "trip_level_od": "Yes",
            "coordinates": "Pickup/drop-off centroids; privacy-rounded census/community areas",
            "timestamps": "Rounded to nearest 15 minutes",
            "economics": "Fare rounded to nearest $2.50; trip total available",
            "license_or_terms": "City of Chicago open data terms",
            "decision": "Best external-city candidate; usable only with centroid/rounding disclosure",
            "paper_action": "Attempt if time permits; otherwise cite as audited but not used because exact-point comparability differs from NYC 2015",
        },
        {
            "candidate": "Porto Taxi Trajectories",
            "source_url": "https://figshare.com/articles/dataset/Porto_taxi_trajectories/12302165",
            "trip_level_od": "Yes",
            "coordinates": "Origin/target GPS points and trajectories",
            "timestamps": "Trip start Unix timestamp",
            "economics": "No comparable fare field in common public release",
            "license_or_terms": "CC BY 4.0 on Figshare derivative",
            "decision": "Useful for route/candidate mechanics, weak for profit/economics",
            "paper_action": "Do not force into primary paper unless economics are explicitly removed",
        },
        {
            "candidate": "Washington DC Taxi",
            "source_url": "https://opendata.dc.gov/",
            "trip_level_od": "Partially",
            "coordinates": "Block/airport-assigned locations in public releases",
            "timestamps": "Often hour-rounded",
            "economics": "Fare fields may exist",
            "license_or_terms": "DC open data terms",
            "decision": "Too coarse for exact-request-window matching",
            "paper_action": "Exclude and soften external-city claims",
        },
        {
            "candidate": "NYC HVFHV / FHV",
            "source_url": "https://data.cityofnewyork.us/Transportation/High-Volume-FHV-filtered-data/ex75-t645",
            "trip_level_od": "Yes",
            "coordinates": "Taxi-zone IDs, not point coordinates",
            "timestamps": "Pickup/drop-off timestamps",
            "economics": "Limited public fare detail; shared-ride flags in some releases",
            "license_or_terms": "NYC Open Data terms",
            "decision": "Ride-hailing context, but not an external city and weaker spatial precision",
            "paper_action": "Mention as future native pooled-request direction, not robustness evidence",
        },
    ]
    portal_candidates = [
        ("San Francisco", "https://data.sfgov.org/"),
        ("Los Angeles", "https://data.lacity.org/"),
        ("Austin", "https://data.austintexas.gov/"),
        ("Seattle", "https://data.seattle.gov/"),
        ("Toronto", "https://open.toronto.ca/"),
        ("Boston", "https://data.boston.gov/"),
        ("Philadelphia", "https://opendataphilly.org/"),
        ("Dallas", "https://www.dallasopendata.com/"),
        ("Houston", "https://data.houstontx.gov/"),
    ]
    for city, source_url in portal_candidates:
        rows.append(
            {
                "candidate": f"{city} municipal open-data portal",
                "source_url": source_url,
                "trip_level_od": "No comparable official trip-level taxi/TNC OD table found in portal audit",
                "coordinates": "Mostly aggregate transportation, permits, incidents, complaints, transit feeds, or non-taxi mobility data",
                "timestamps": "Not comparable for public taxi/TNC OD matching",
                "economics": "Not comparable for public taxi/TNC scenario-profit evaluation",
                "license_or_terms": "City portal terms vary by dataset",
                "decision": "No clean match found",
                "paper_action": "Do not add weak data; state public external-city limitation",
            }
        )
    pd.DataFrame(rows).to_csv(RESULTS / "external_dataset_audit.csv", index=False)


def _write_prior_work_positioning() -> None:
    rows = [
        ("T-Share / dynamic taxi ridesharing", "spatiotemporal indexing and dynamic matching", "public-data route-corridor exposure with exact post-retrieval eligibility", "We do not reproduce T-Share fleet optimization; we compare the retrieval primitive and dispatch-lite layer."),
        ("Shareability networks", "compatibility under time/delay windows", "route-specific candidate-pool construction over OSRM alternatives", "Shareability is an inspiration, not a direct baseline."),
        ("Dynamic trip-vehicle assignment", "global assignment over requests and vehicles", "low-latency route-choice layer before assignment", "Our simulator is not a replacement for full RTV/global optimization."),
        ("Rolling-horizon dispatch studies", "batching and online reassignment", "60-second shared-request route-choice evaluation", "We add rider exclusivity but not repositioning or long-horizon fleet control."),
        ("Path-buffer/geometric retrieval", "simple route-neighborhood exposure", "H3 pickup-and-drop-off corridor eligibility plus exact timing", "Now included as a bounded sanity baseline."),
        ("Learning-based dispatch/ranking", "ML value estimation or order assignment", "learned route ranking after explicit candidate construction", "ML is a residual scorer, not the primary source of lift."),
    ]
    pd.DataFrame(rows, columns=["literature_family", "reused_or_related_idea", "paper_specific_contribution", "scope_boundary"]).to_csv(
        RESULTS / "prior_work_positioning.csv", index=False
    )


def _write_proxy_summary(drivers: pd.DataFrame, riders: pd.DataFrame) -> None:
    rows = []
    for split in ("train", "test"):
        d = drivers.loc[drivers["split"] == split, "trip_distance_miles"]
        r = riders.loc[riders["split"] == split, "trip_distance_miles"]
        rows.append({
            "split": split,
            "proxy_role": "driver",
            "retained_rows": int(d.shape[0]),
            "distance_min": float(d.min()),
            "distance_p25": float(d.quantile(0.25)),
            "distance_median": float(d.median()),
            "distance_p75": float(d.quantile(0.75)),
            "distance_max": float(d.max()),
            "retained_sample_semantics": "Trips longer than 10 miles",
        })
        rows.append({
            "split": split,
            "proxy_role": "rider",
            "retained_rows": int(r.shape[0]),
            "distance_min": float(r.min()),
            "distance_p25": float(r.quantile(0.25)),
            "distance_median": float(r.median()),
            "distance_p75": float(r.quantile(0.75)),
            "distance_max": float(r.max()),
            "retained_sample_semantics": "25% sample of eligible 0.5-10 mile trips",
        })
    pd.DataFrame(rows).to_csv(RESULTS / "proxy_role_distribution_summary.csv", index=False)

    threshold_rows = []
    for driver_min in (8, 10, 12):
        if driver_min < 10:
            retained_rows = np.nan
            note = "Not observable from the processed driver file because it stores only >10 mile trips; requires raw-data rerun."
        else:
            retained_rows = int((drivers["trip_distance_miles"] > driver_min).sum())
            note = "Exact count from processed driver file."
        threshold_rows.append({
            "role": "driver",
            "threshold": f"trip_distance_miles > {driver_min}",
            "retained_rows": retained_rows,
            "estimated_rows_before_presample": np.nan,
            "observability_note": note,
        })
    for rider_max in (8, 10, 12):
        if rider_max > 10:
            sampled_rows = np.nan
            estimated_rows = np.nan
            note = "Not observable from the processed rider file because it stores only the 0.5-10 mile retained sample; requires raw-data rerun."
        else:
            sampled_rows = int(riders["trip_distance_miles"].between(0.5, rider_max).sum())
            estimated_rows = int(round(sampled_rows / 0.25))
            note = "Estimated from the checked-in 25% retained rider sample."
        threshold_rows.append({
            "role": "rider",
            "threshold": f"0.5 <= trip_distance_miles <= {rider_max}",
            "retained_rows": sampled_rows,
            "estimated_rows_before_presample": estimated_rows,
            "observability_note": note,
        })
    pd.DataFrame(threshold_rows).to_csv(RESULTS / "proxy_threshold_sensitivity.csv", index=False)


def _route_profit(route, matched: list[dict], cost_per_mile: float = 0.67) -> float:
    revenue = sum(row["fare_share"] for row in matched)
    cost = (route.distance_m / METERS_PER_MILE) * cost_per_mile
    return float(revenue - cost)


def _optimal_assignment(feasible: list[dict], seats: int = 3) -> tuple[float, int]:
    best_revenue = 0.0
    best_count = 0
    usable = feasible[:18]
    for k in range(1, min(len(usable), seats) + 1):
        for combo in itertools.combinations(usable, k):
            pax = sum(int(row["passenger_count"]) for row in combo)
            if pax <= seats:
                revenue = sum(float(row["fare_share"]) for row in combo)
                if revenue > best_revenue:
                    best_revenue = revenue
                    best_count = len(combo)
    return best_revenue, best_count


def _time_filtered_subset(rider_index: RiderIndex, indices: np.ndarray, query_ts: pd.Timestamp, max_request_offset_min: int) -> pd.DataFrame:
    if indices.size == 0:
        return rider_index.riders.iloc[0:0]
    subset = rider_index.riders.iloc[indices]
    delta_s = (subset["pickup_datetime"] - query_ts).dt.total_seconds().abs()
    return subset.loc[delta_s <= max_request_offset_min * 60]


def _rule_candidates(rider_index: RiderIndex, corridor_cells, query_ts: pd.Timestamp, rule: str, max_request_offset_min: int) -> pd.DataFrame:
    center_bucket = query_ts.floor(rider_index._bucket_freq)
    buckets = [
        center_bucket + pd.Timedelta(minutes=rider_index._index_bin_minutes * d)
        for d in (-1, 0, 1)
    ]
    pickup = rider_index._gather_indices_np(corridor_cells, rider_index._pickup_idx, buckets)
    dropoff = rider_index._gather_indices_np(corridor_cells, rider_index._dropoff_idx, buckets)
    if rule == "pickup_only":
        indices = pickup
    elif rule == "dropoff_only":
        indices = dropoff
    elif rule == "pickup_and_dropoff":
        indices = np.intersect1d(pickup, dropoff)
    else:
        raise ValueError(rule)
    return _time_filtered_subset(rider_index, indices, query_ts, max_request_offset_min)


def _write_route_evidence(drivers: pd.DataFrame, riders: pd.DataFrame, sample: int) -> None:
    domain_config = get_domain_config("yellow")
    router = OSRMRouter(cache_path=domain_config.route_cache_path, cache_only=True, rate_limit=False)
    # The checked-in route cache is intentionally small, so scan well beyond
    # the requested hit count and stop once enough cached OD pairs are found.
    test_drivers = drivers.loc[drivers["split"] == "test"].reset_index(drop=True)
    test_riders = riders.loc[riders["split"] == "test"].reset_index(drop=True)
    rider_index = RiderIndex(test_riders, index_bin_minutes=15)
    trips = build_driver_trips(
        test_drivers,
        seats=3,
        max_detour_min=4.0,
        platform_share=0.50,
        cost_per_mile=0.67,
        urban_speed_kmh=40.0,
    )

    overlap_rows = []
    ablation_rows = []
    assignment_rows = []
    runtime_rows = []
    collected = 0
    cache_hits = 0
    cache_misses = 0

    for idx, trip in enumerate(trips):
        if collected >= sample:
            break
        t_route = time.perf_counter()
        routes = router.get_alternative_routes(trip.origin, trip.destination, max_alternatives=3)
        route_s = time.perf_counter() - t_route
        if not routes:
            cache_misses += 1
            continue
        cache_hits += 1
        if len(routes) < 2:
            continue

        t_corridor = time.perf_counter()
        corridors = [build_corridor(route.polyline, resolution=9, buffer_rings=1, densify_step_m=80.0) for route in routes]
        corridor_s = time.perf_counter() - t_corridor

        route_sets = []
        candidate_sets = []
        feasible_sets = []
        route_profits = []
        filter_s_total = 0.0

        for route_idx, (route, corridor) in enumerate(zip(routes, corridors)):
            t_filter = time.perf_counter()
            candidates, stats = rider_index.find_in_corridor_with_stats(
                corridor.corridor_cells,
                trip.minute_of_day,
                window_bins=1,
                max_request_offset_min=5,
                query_datetime=trip.departure_time,
            )
            matched, feasible = match_riders(
                corridor,
                route.polyline,
                rider_index,
                minute_of_day=trip.minute_of_day,
                query_datetime=trip.departure_time,
                seats=3,
                max_detour_min=4.0,
                candidate_window_bins=1,
                max_request_offset_min=5,
                platform_share=0.50,
                urban_speed_kmh=40.0,
                seed=42,
                candidates=candidates,
            )
            filter_s_total += time.perf_counter() - t_filter
            route_sets.append(set(corridor.corridor_cells))
            candidate_sets.append(set(candidates.index.tolist()))
            feasible_sets.append({row["rider_idx"] for row in feasible})
            route_profits.append(_route_profit(route, matched))

            for rule in ("pickup_only", "dropoff_only", "pickup_and_dropoff"):
                rule_df = _rule_candidates(rider_index, corridor.corridor_cells, pd.Timestamp(trip.departure_time), rule, 5)
                ablation_rows.append({
                    "driver_id": collected,
                    "route_idx": route_idx,
                    "eligibility_rule": rule,
                    "exact_time_candidates": int(len(rule_df)),
                    "feasible_after_detour_seat": int(len(feasible)) if rule == "pickup_and_dropoff" else "",
                })
            greedy_revenue = sum(row["fare_share"] for row in matched)
            optimal_revenue, optimal_count = _optimal_assignment(feasible, seats=3)
            assignment_rows.append({
                "driver_id": collected,
                "route_idx": route_idx,
                "feasible_count": len(feasible),
                "greedy_revenue": greedy_revenue,
                "optimal_revenue": optimal_revenue,
                "greedy_minus_optimal": greedy_revenue - optimal_revenue,
                "greedy_matched": len(matched),
                "optimal_matched": optimal_count,
            })

        for a, b in itertools.combinations(range(len(routes)), 2):
            overlap_rows.append({
                "driver_id": collected,
                "route_pair": f"{a}-{b}",
                "route_cell_jaccard": len(route_sets[a] & route_sets[b]) / max(len(route_sets[a] | route_sets[b]), 1),
                "candidate_jaccard": len(candidate_sets[a] & candidate_sets[b]) / max(len(candidate_sets[a] | candidate_sets[b]), 1),
                "feasible_jaccard": len(feasible_sets[a] & feasible_sets[b]) / max(len(feasible_sets[a] | feasible_sets[b]), 1),
                "default_route_profit": route_profits[0],
                "best_alt_profit": max(route_profits),
                "best_alt_minus_default": max(route_profits) - route_profits[0],
            })

        runtime_rows.append({
            "driver_id": collected,
            "routes_returned": len(routes),
            "cache_lookup_s": route_s,
            "corridor_build_s": corridor_s,
            "candidate_filter_and_match_s": filter_s_total,
            "end_to_end_cached_s": route_s + corridor_s + filter_s_total,
            "cache_hits_so_far": cache_hits,
            "cache_misses_so_far": cache_misses,
        })
        collected += 1

    pd.DataFrame(overlap_rows).to_csv(RESULTS / "route_alternative_overlap_summary.csv", index=False)
    pd.DataFrame(ablation_rows).to_csv(RESULTS / "eligibility_rule_ablation.csv", index=False)
    pd.DataFrame(assignment_rows).to_csv(RESULTS / "greedy_vs_optimal_assignment.csv", index=False)
    runtime = pd.DataFrame(runtime_rows)
    if not runtime.empty:
        runtime_summary = runtime[["cache_lookup_s", "corridor_build_s", "candidate_filter_and_match_s", "end_to_end_cached_s"]].agg(["mean", "median", "max"]).reset_index(names="stat")
        runtime_summary["drivers_profiled"] = len(runtime)
        runtime_summary["cache_hits"] = cache_hits
        runtime_summary["cache_misses"] = cache_misses
        runtime_summary["route_cache_entries"] = _route_cache_entries(domain_config.route_cache_path)
        runtime_summary.to_csv(RESULTS / "end_to_end_runtime_profile.csv", index=False)
    else:
        pd.DataFrame().to_csv(RESULTS / "end_to_end_runtime_profile.csv", index=False)


def _route_cache_entries(path: Path) -> int:
    if not path.exists():
        return 0
    con = sqlite3.connect(path)
    try:
        return int(con.execute("SELECT COUNT(*) FROM routes").fetchone()[0])
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reviewer-revision evidence tables")
    parser.add_argument("--sample", type=int, default=100, help="Cached-route test drivers to profile")
    args = parser.parse_args()

    RESULTS.mkdir(exist_ok=True)
    config = get_domain_config("yellow")
    drivers = pd.read_parquet(config.drivers_path(), columns=DRIVER_COLS)
    riders = pd.read_parquet(config.riders_path(), columns=RIDER_COLS)

    _write_feature_dictionary()
    _write_external_dataset_audit()
    _write_prior_work_positioning()
    _write_proxy_summary(drivers, riders)
    _write_route_evidence(drivers, riders, sample=args.sample)
    print("Reviewer revision evidence written to results/.")


if __name__ == "__main__":
    main()
