from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_prep.domain_config import get_domain_config
from simulation.domain_io import build_driver_trips
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe live OSRM route-fetch latency on a tiny public-server sample.")
    parser.add_argument("--sample", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    config = get_domain_config("yellow")
    drivers = pd.read_parquet(config.drivers_path(), columns=DRIVER_COLS)
    drivers = drivers.loc[drivers["split"] == "test"].sample(n=args.sample, random_state=args.seed).reset_index(drop=True)
    trips = build_driver_trips(
        drivers,
        seats=3,
        max_detour_min=4,
        platform_share=0.50,
        cost_per_mile=0.67,
        urban_speed_kmh=40,
    )

    temp_dir = Path(tempfile.mkdtemp(prefix="osrm_latency_probe_"))
    try:
        router = OSRMRouter(cache_path=temp_dir / "route_cache_probe.db", cache_only=False)
        rows = []
        for trip in trips:
            t0 = time.perf_counter()
            ok = True
            error = ""
            routes = []
            try:
                routes = router.get_alternative_routes(trip.origin, trip.destination, max_alternatives=3)
            except Exception as exc:  # pragma: no cover - network diagnostic
                ok = False
                error = str(exc)
            latency_s = time.perf_counter() - t0
            rows.append(
                {
                    "driver_id": trip.driver_id,
                    "ok": ok,
                    "route_count": len(routes),
                    "latency_s": latency_s,
                    "error": error,
                    "note": "Tiny public OSRM probe; not a production latency guarantee.",
                }
            )
        router.flush_cache()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    raw = pd.DataFrame(rows)
    ok_rows = raw.loc[raw["ok"]]
    summary = pd.DataFrame(
        [
            {
                "requests": int(ok_rows.shape[0]),
                "mean_latency_s": float(ok_rows["latency_s"].mean()) if not ok_rows.empty else 0.0,
                "median_latency_s": float(ok_rows["latency_s"].median()) if not ok_rows.empty else 0.0,
                "max_latency_s": float(ok_rows["latency_s"].max()) if not ok_rows.empty else 0.0,
                "mean_route_count": float(ok_rows["route_count"].mean()) if not ok_rows.empty else 0.0,
                "sample": args.sample,
                "seed": args.seed,
                "note": "Public OSRM live route-fetch probe; cached online dispatch timings are reported separately.",
            }
        ]
    )

    raw.to_csv(RESULTS / "osrm_live_latency_probe_raw.csv", index=False)
    summary.to_csv(RESULTS / "osrm_live_latency_probe.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
