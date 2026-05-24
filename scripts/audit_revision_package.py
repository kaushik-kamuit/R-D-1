from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


CHECKS = [
    ("paper", "manuscript_source", ROOT / "paper" / "ieee_submission.tex", True, "LaTeX manuscript source."),
    ("paper", "compiled_pdf", ROOT / "paper" / "ieee_submission.pdf", True, "Locally compiled clean manuscript PDF."),
    ("paper", "response_draft", ROOT / "paper" / "response_to_reviewers_draft.md", True, "Draft response mapped to reviewer comments."),
    ("paper", "handoff_notes", ROOT / "paper" / "revision_handoff_notes.md", True, "Current revision handoff notes."),
    ("paper", "artifact_manifest", RESULTS / "revision_artifact_manifest.csv", True, "Machine-readable artifact-to-generator manifest."),
    ("paper", "reviewer_response_matrix", RESULTS / "reviewer_response_matrix.csv", True, "One-row-per-comment response coverage matrix."),
    ("paper", "reviewer_response_traceability", RESULTS / "reviewer_response_traceability.csv", True, "Response-matrix artifact and manuscript-label traceability audit."),
    ("model", "yellow_profit_model", ROOT / "models" / "yellow" / "profit_model_v2.pkl", False, "Needed to rerun full warm-up dispatch from scratch."),
    ("model", "legacy_yellow_profit_model", ROOT / "models" / "profit_model_v2.pkl", False, "Legacy fallback model path used by some older scripts."),
    ("dataset", "yellow_training_dataset", ROOT / "data" / "ml" / "yellow" / "training_dataset_v2.parquet", False, "Needed to retrain the Yellow model."),
    ("dataset", "legacy_training_dataset", ROOT / "data" / "ml" / "training_dataset_v2.parquet", False, "Legacy fallback training dataset path."),
    ("dispatch", "raw_dispatch_outcomes", ROOT / "results" / "dispatch" / "yellow" / "primary_dispatch_d10_w5_det4" / "dispatch_outcomes.csv", False, "Needed for fresh driver-level dispatch bootstrap tests."),
    ("dispatch", "primary_dispatch_summary", RESULTS / "dispatch_yellow_primary.csv", True, "Checked-in primary dispatch summary."),
    ("reviewer", "path_buffer_comparison", RESULTS / "path_buffer_baseline_comparison.csv", True, "1000-driver path-buffer comparator."),
    ("reviewer", "route_overlap", RESULTS / "route_alternative_overlap_summary.csv", True, "OSRM route/candidate-pool overlap evidence."),
    ("reviewer", "eligibility_ablation", RESULTS / "eligibility_rule_ablation.csv", True, "Pickup/dropoff/feasibility ablation."),
    ("reviewer", "runtime_profile", RESULTS / "end_to_end_runtime_profile.csv", True, "Cached end-to-end runtime profile."),
    ("reviewer", "runtime_resource_summary", RESULTS / "runtime_resource_summary.csv", True, "Route-cache storage and single-lookup memory-footprint summary."),
    ("reviewer", "validation_heuristic", RESULTS / "validation_heuristic_selection.csv", True, "March validation-selected heuristic evidence."),
    ("reviewer", "retained_density_sensitivity", RESULTS / "retained_density_sensitivity.csv", True, "Dispatch density sensitivity over the fixed retained rider sample."),
    ("reviewer", "dispatch_corridor_sensitivity", RESULTS / "dispatch_corridor_sensitivity.csv", True, "Dispatch-level corridor sensitivity diagnostic."),
    ("reviewer", "dispatch_policy_gap_summary", RESULTS / "dispatch_policy_gap_summary.csv", True, "Seed-level dispatch policy-gap summary for uncertainty comments."),
    ("reviewer", "dispatch_uncertainty_summary", RESULTS / "dispatch_uncertainty_summary.csv", True, "Dispatch CI-width audit for reviewer uncertainty comments."),
]


def _status(exists: bool, expected_for_review: bool) -> str:
    if exists:
        return "present"
    return "missing_packaging_gap" if expected_for_review else "missing_regeneration_artifact"


def _handoff_action(status: str, expected_for_review: bool) -> str:
    if status == "present" and expected_for_review:
        return "Include or cite in the review-facing revision package."
    if status == "present":
        return "Optional local support artifact; include in a release only if size/license permits."
    if status == "missing_regeneration_artifact":
        return "Does not block the current reviewer evidence package; regenerate or publish as a release asset before claiming full raw rerun support."
    return "Blocks the review-facing package until restored."


def _route_cache_entries(path: Path) -> int | None:
    if not path.exists():
        return None
    con = sqlite3.connect(path)
    try:
        return int(con.execute("SELECT COUNT(*) FROM routes").fetchone()[0])
    finally:
        con.close()


def main() -> None:
    rows: list[dict[str, object]] = []
    for category, name, path, expected_for_review, note in CHECKS:
        exists = path.exists()
        status = _status(exists, expected_for_review)
        rows.append(
            {
                "category": category,
                "artifact": name,
                "path": str(path.relative_to(ROOT)),
                "exists": exists,
                "size_bytes": path.stat().st_size if exists and path.is_file() else 0,
                "expected_for_review": expected_for_review,
                "status": status,
                "handoff_action": _handoff_action(status, expected_for_review),
                "note": note,
            }
        )

    cache_path = ROOT / "data" / "route_cache_yellow.db"
    cache_entries = _route_cache_entries(cache_path)
    cache_status = "present" if cache_entries and cache_entries >= 1000 else "needs_attention"
    rows.append(
        {
            "category": "route_cache",
            "artifact": "yellow_route_cache_entries",
            "path": str(cache_path.relative_to(ROOT)),
            "exists": cache_path.exists(),
            "size_bytes": cache_path.stat().st_size if cache_path.exists() else 0,
            "expected_for_review": True,
            "status": cache_status,
            "handoff_action": _handoff_action(cache_status, True),
            "note": f"SQLite route cache entries={cache_entries}; 1000+ expected after path-buffer rerun.",
        }
    )

    out = RESULTS / "revision_package_audit.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    missing_review = [row for row in rows if row["expected_for_review"] and row["status"] != "present"]
    print(f"Wrote {out.relative_to(ROOT)}")
    if missing_review:
        print("Review-facing packaging gaps remain:")
        for row in missing_review:
            print(f"  - {row['artifact']}: {row['path']} ({row['status']})")
    else:
        print("All review-facing audit artifacts are present.")


if __name__ == "__main__":
    main()
