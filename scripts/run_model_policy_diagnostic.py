from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_prep.domain_config import get_domain_config
from matching.matcher import METERS_PER_MILE, match_riders
from matching.rider_index import RiderIndex
from models.predict import FEATURE_COLS
from simulation.domain_io import build_driver_trips, load_h3_stats_dict
from simulation.warmup import _route_features
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
]


def _build_cached_route_dataset(sample: int, density_pct: int, seed: int) -> pd.DataFrame:
    config = get_domain_config("yellow")
    drivers = pd.read_parquet(config.drivers_path(), columns=DRIVER_COLS)
    drivers = drivers.loc[drivers["split"] == "test"].reset_index(drop=True)
    riders = pd.read_parquet(config.riders_path(), columns=RIDER_COLS)
    riders = riders.loc[riders["split"] == "test"].reset_index(drop=True)
    if density_pct < 100:
        riders = riders.sample(frac=density_pct / 100.0, random_state=seed).reset_index(drop=True)

    rider_index = RiderIndex(riders, index_bin_minutes=15)
    h3_stats = load_h3_stats_dict(config)
    router = OSRMRouter(cache_path=config.route_cache_path, cache_only=True)
    trips = build_driver_trips(
        drivers,
        seats=3,
        max_detour_min=4,
        platform_share=0.50,
        cost_per_mile=0.67,
        urban_speed_kmh=40,
    )

    rows: list[dict[str, float | int | str]] = []
    kept_drivers = 0
    for frame_idx, trip in enumerate(trips):
        routes = router.get_alternative_routes(trip.origin, trip.destination, max_alternatives=3)
        if len(routes) < 2:
            continue
        driver_row = drivers.iloc[frame_idx]
        for route_idx, route in enumerate(routes):
            corridor = build_corridor(route.polyline, resolution=9, buffer_rings=1, densify_step_m=80.0)
            candidates = rider_index.find_in_corridor(
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
                seats=trip.seats,
                max_detour_min=trip.max_detour_minutes,
                max_request_offset_min=5,
                platform_share=trip.platform_share,
                urban_speed_kmh=trip.urban_speed_kmh,
                seed=seed,
                candidates=candidates,
            )
            features = _route_features(
                route,
                corridor,
                rider_index,
                route.polyline,
                trip.minute_of_day,
                trip.hour,
                int(driver_row["day_of_week"]),
                int(driver_row["is_weekend"]),
                int(pd.Timestamp(driver_row["pickup_datetime"]).day),
                trip.origin,
                trip.destination,
                h3_stats,
                seats=trip.seats,
                max_detour_min=trip.max_detour_minutes,
                candidate_window_bins=1,
                max_request_offset_min=5,
                query_datetime=trip.departure_time,
                candidates=candidates,
            )
            revenue = sum(row["fare_share"] for row in matched)
            cost = (route.distance_m / METERS_PER_MILE) * trip.cost_per_mile
            rows.append(
                {
                    "driver_id": kept_drivers,
                    "frame_idx": frame_idx,
                    "route_idx": route_idx,
                    "actual_profit": float(revenue - cost),
                    "matched_riders": len(matched),
                    "feasible_count": len(feasible),
                    **features,
                }
            )
        kept_drivers += 1
        if kept_drivers >= sample:
            break
    return pd.DataFrame(rows)


def _policy_eval(df: pd.DataFrame, pred_col: str, label: str) -> dict[str, float | str | int]:
    profits = []
    rank_correct = 0
    total = 0
    for _driver_id, group in df.groupby("driver_id"):
        if len(group) < 2:
            continue
        chosen = group.loc[group[pred_col].idxmax()]
        oracle = group.loc[group["actual_profit"].idxmax()]
        profits.append(float(chosen["actual_profit"]))
        rank_correct += int(chosen["route_idx"] == oracle["route_idx"])
        total += 1
    return {
        "model": label,
        "policy_profit_per_driver": float(np.mean(profits)) if profits else 0.0,
        "rank1_accuracy": rank_correct / max(total, 1),
        "drivers_evaluated": total,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train model-family route-rankers on cached route alternatives and report held-out policy profit.")
    parser.add_argument("--sample", type=int, default=140)
    parser.add_argument("--density-pct", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = _build_cached_route_dataset(args.sample, args.density_pct, args.seed)
    if df.empty:
        raise RuntimeError("No cached multi-route driver data available.")
    driver_ids = np.array(sorted(df["driver_id"].unique()))
    rng = np.random.default_rng(args.seed)
    rng.shuffle(driver_ids)
    split_at = max(1, int(0.7 * len(driver_ids)))
    train_drivers = set(driver_ids[:split_at].tolist())
    train_df = df.loc[df["driver_id"].isin(train_drivers)].copy()
    test_df = df.loc[~df["driver_id"].isin(train_drivers)].copy()

    X_train = train_df[FEATURE_COLS].to_numpy(dtype=np.float32)
    y_train = train_df["actual_profit"].to_numpy(dtype=np.float32)
    X_test = test_df[FEATURE_COLS].to_numpy(dtype=np.float32)
    y_test = test_df["actual_profit"].to_numpy(dtype=np.float32)

    rows = []
    test_df["coldstart_score"] = -test_df["route_idx"]
    test_df["oracle_score"] = test_df["actual_profit"]
    rows.append(_policy_eval(test_df, "coldstart_score", "Cold-start default"))
    rows.append(_policy_eval(test_df, "oracle_score", "Oracle route set"))

    models = [
        ("Ridge", make_pipeline(StandardScaler(), Ridge(alpha=1.0))),
        ("MLP", make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500, random_state=args.seed))),
    ]
    try:
        import lightgbm as lgb

        models.extend(
            [
                (
                    "LightGBM baseline",
                    lgb.LGBMRegressor(
                        objective="regression",
                        learning_rate=0.05,
                        num_leaves=31,
                        n_estimators=200,
                        random_state=args.seed,
                        verbose=-1,
                    ),
                ),
                (
                    "LightGBM tuned",
                    lgb.LGBMRegressor(
                        objective="regression",
                        learning_rate=0.03,
                        num_leaves=63,
                        max_depth=8,
                        n_estimators=400,
                        min_child_samples=10,
                        random_state=args.seed,
                        verbose=-1,
                    ),
                ),
            ]
        )
    except Exception:
        lgb = None

    for label, model in models:
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        col = f"pred_{label}".replace(" ", "_")
        test_df[col] = pred
        row = _policy_eval(test_df, col, label)
        row["r2"] = float(r2_score(y_test, pred)) if len(y_test) > 1 else 0.0
        row["rmse"] = float(np.sqrt(mean_squared_error(y_test, pred))) if len(y_test) > 0 else 0.0
        rows.append(row)

    if "lgb" in locals() and lgb is not None:
        rank_train = train_df.sort_values(["driver_id", "route_idx"]).copy()
        rank_test = test_df.sort_values(["driver_id", "route_idx"]).copy()
        rank_labels = (
            rank_train.groupby("driver_id")["actual_profit"]
            .rank(method="first")
            .astype(int)
            .to_numpy()
        )
        rank_groups = rank_train.groupby("driver_id").size().to_list()
        ranker = lgb.LGBMRanker(
            objective="lambdarank",
            learning_rate=0.05,
            num_leaves=15,
            n_estimators=100,
            random_state=args.seed,
            verbose=-1,
        )
        ranker.fit(rank_train[FEATURE_COLS], rank_labels, group=rank_groups)
        rank_col = "pred_LambdaRank"
        test_df[rank_col] = ranker.predict(test_df[FEATURE_COLS])
        rows.append(_policy_eval(test_df, rank_col, "LambdaRank"))

    out = pd.DataFrame(rows)
    out["sample_scope"] = "cached_multiroute_april_yellow_route_policy_diagnostic"
    out["density_pct"] = args.density_pct
    out["seed"] = args.seed
    out["note"] = "Held-out cached route-choice diagnostic; narrower than full rolling dispatch."
    out.to_csv(RESULTS / "model_policy_diagnostic.csv", index=False)
    df.to_csv(RESULTS / "model_policy_diagnostic_dataset.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
