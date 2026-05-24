from __future__ import annotations

import json
import sqlite3
import tracemalloc
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CACHE = ROOT / "data" / "route_cache_yellow.db"


def _cache_stats() -> dict[str, float]:
    if not CACHE.exists():
        raise SystemExit(f"Missing route cache: {CACHE.relative_to(ROOT)}")
    con = sqlite3.connect(CACHE)
    try:
        entries = int(con.execute("SELECT COUNT(*) FROM routes").fetchone()[0])
        avg_payload, max_payload = con.execute(
            "SELECT AVG(LENGTH(routes_json)), MAX(LENGTH(routes_json)) FROM routes"
        ).fetchone()
        page_count = int(con.execute("PRAGMA page_count").fetchone()[0])
        page_size = int(con.execute("PRAGMA page_size").fetchone()[0])
        sample = con.execute("SELECT routes_json FROM routes LIMIT 1").fetchone()[0]
    finally:
        con.close()

    tracemalloc.start()
    con = sqlite3.connect(CACHE)
    try:
        row = con.execute("SELECT routes_json FROM routes LIMIT 1").fetchone()
        if row is not None:
            json.loads(row[0])
        _, peak = tracemalloc.get_traced_memory()
    finally:
        con.close()
        tracemalloc.stop()

    return {
        "route_cache_entries": entries,
        "route_cache_file_mb": CACHE.stat().st_size / (1024 * 1024),
        "sqlite_page_footprint_mb": page_count * page_size / (1024 * 1024),
        "avg_route_payload_kb": float(avg_payload or 0) / 1024,
        "max_route_payload_kb": float(max_payload or 0) / 1024,
        "sample_route_payload_kb": len(sample) / 1024,
        "traced_peak_single_lookup_mb": peak / (1024 * 1024),
    }


def main() -> None:
    runtime = pd.read_csv(RESULTS / "end_to_end_runtime_profile.csv")
    osrm = pd.read_csv(RESULTS / "osrm_live_latency_probe.csv").iloc[0]
    mean_runtime = runtime.loc[runtime["stat"] == "mean"].iloc[0]
    max_runtime = runtime.loc[runtime["stat"] == "max"].iloc[0]

    row = {
        **_cache_stats(),
        "drivers_profiled": int(mean_runtime["drivers_profiled"]),
        "profiled_cache_hits": int(mean_runtime["cache_hits"]),
        "profiled_cache_misses": int(mean_runtime["cache_misses"]),
        "mean_cached_total_ms": float(mean_runtime["end_to_end_cached_s"]) * 1000,
        "max_cached_total_ms": float(max_runtime["end_to_end_cached_s"]) * 1000,
        "live_osrm_requests": int(osrm["requests"]),
        "live_osrm_mean_latency_s": float(osrm["mean_latency_s"]),
        "live_osrm_median_latency_s": float(osrm["median_latency_s"]),
    }
    out = RESULTS / "runtime_resource_summary.csv"
    pd.DataFrame([row]).to_csv(out, index=False)
    print(
        f"Wrote {out.relative_to(ROOT)}: cache={row['route_cache_file_mb']:.1f} MB, "
        f"single-lookup traced peak={row['traced_peak_single_lookup_mb']:.3f} MB"
    )


if __name__ == "__main__":
    main()
