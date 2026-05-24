from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


ARTIFACTS = [
    ("paper", "paper/ieee_submission.tex", "manual manuscript source", "Main revised manuscript source."),
    ("paper", "paper/ieee_submission.pdf", "pdflatex/bibtex build", "Locally compiled clean manuscript PDF."),
    ("paper", "paper/response_to_reviewers_draft.md", "manual response draft", "Draft response-to-reviewers source."),
    ("paper", "paper/revision_handoff_notes.md", "manual handoff notes", "Current technical handoff for the next agent/author."),
    ("reviewer", "results/prior_work_positioning.csv", "scripts/run_reviewer_revision_evidence.py", "Novelty and prior-work positioning table."),
    ("reviewer", "results/external_dataset_audit.csv", "scripts/run_reviewer_revision_evidence.py", "Major public external-city dataset audit."),
    ("reviewer", "results/proxy_role_distribution_summary.csv", "scripts/run_reviewer_revision_evidence.py", "Proxy driver/rider retained-count and distance summary."),
    ("reviewer", "results/proxy_threshold_sensitivity.csv", "scripts/run_reviewer_revision_evidence.py", "Observable proxy-threshold sensitivity audit."),
    ("reviewer", "results/reviewer_feature_dictionary.csv", "scripts/run_reviewer_revision_evidence.py", "Feature dictionary with availability and leakage status."),
    ("reviewer", "results/route_alternative_overlap_summary.csv", "scripts/run_reviewer_revision_evidence.py", "OSRM alternative overlap and default-route comparison evidence."),
    ("reviewer", "results/eligibility_rule_ablation.csv", "scripts/run_reviewer_revision_evidence.py", "Pickup/drop-off eligibility-rule ablation."),
    ("reviewer", "results/greedy_vs_optimal_assignment.csv", "scripts/run_reviewer_revision_evidence.py", "Greedy seat-fill versus exhaustive small-batch assignment."),
    ("reviewer", "results/end_to_end_runtime_profile.csv", "scripts/run_reviewer_revision_evidence.py", "Cached route lookup/corridor/filter/matching timing."),
    ("reviewer", "results/runtime_resource_summary.csv", "scripts/build_runtime_resource_summary.py", "Route-cache storage and single-lookup memory-footprint summary."),
    ("reviewer", "results/stronger_dispatch_baselines.csv", "scripts/run_stronger_dispatch_baselines.py", "Greedy nearest-route and batch bipartite dispatch diagnostics."),
    ("reviewer", "results/osrm_live_latency_probe.csv", "scripts/profile_osrm_live_latency.py", "Live public OSRM route-fetch latency probe summary."),
    ("reviewer", "results/osrm_live_latency_probe_raw.csv", "scripts/profile_osrm_live_latency.py", "Live public OSRM route-fetch latency raw rows."),
    ("reviewer", "results/model_policy_diagnostic.csv", "scripts/run_model_policy_diagnostic.py", "Cached route-policy comparison across model families."),
    ("reviewer", "results/model_policy_diagnostic_dataset.csv", "scripts/run_model_policy_diagnostic.py", "Held-out cached route-policy diagnostic dataset."),
    ("reviewer", "results/validation_heuristic_selection.csv", "scripts/run_validation_heuristic_selection.py", "March validation-selected non-ML heuristic summary."),
    ("reviewer", "results/validation_heuristic_selection_raw.csv", "scripts/run_validation_heuristic_selection.py", "Raw March validation heuristic rows."),
    ("reviewer", "results/retained_density_sensitivity.csv", "scripts/build_retained_density_sensitivity.py", "Retained-rider density sensitivity over the fixed 25% sample."),
    ("reviewer", "results/dispatch_corridor_sensitivity.csv", "scripts/run_dispatch_corridor_sensitivity.py", "Cached dispatch-level H3/k-ring/densification diagnostic."),
    ("reviewer", "results/path_buffer_single_driver_summary.csv", "scripts/run_path_buffer_baseline.py", "Path-buffer single-driver comparator."),
    ("reviewer", "results/path_buffer_dispatch_summary.csv", "scripts/run_path_buffer_baseline.py", "Path-buffer dispatch comparator summary."),
    ("reviewer", "results/path_buffer_baseline_comparison.csv", "scripts/run_path_buffer_baseline.py", "1000-driver live-or-cached path-buffer comparison."),
    ("reviewer", "results/path_buffer_baseline_config.json", "scripts/run_path_buffer_baseline.py", "Path-buffer rerun configuration."),
    ("reviewer", "results/dispatch_policy_gap_summary.csv", "scripts/build_dispatch_policy_gap_summary.py", "Seed-level dispatch policy-gap summary."),
    ("reviewer", "results/dispatch_uncertainty_summary.csv", "scripts/build_dispatch_uncertainty_summary.py", "Dispatch CI-width audit across headline and density-sweep metrics."),
    ("reviewer", "results/reviewer_response_matrix.csv", "scripts/build_reviewer_response_matrix.py", "One-row-per-comment reviewer response coverage matrix."),
    ("reviewer", "results/reviewer_response_traceability.csv", "scripts/audit_reviewer_response_traceability.py", "Checks that response-matrix artifact and table references resolve."),
    ("reviewer", "results/revision_package_audit.csv", "scripts/audit_revision_package.py", "Review-facing artifact package audit."),
    ("figure", "paper/figures/paper_fig5a_gain_composition.png", "visualizations/plot_paper_figures.py", "Split Figure 5 gain-composition panel."),
    ("figure", "paper/figures/paper_fig5b_residual_ml_lift.png", "visualizations/plot_paper_figures.py", "Split Figure 5 residual-ML-lift panel."),
]


def main() -> None:
    rows = []
    for category, path_text, generator, purpose in ARTIFACTS:
        path = ROOT / path_text
        rows.append(
            {
                "category": category,
                "artifact_path": path_text,
                "generator_or_source": generator,
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
                "purpose": purpose,
            }
        )
    out = ROOT / "results" / "revision_artifact_manifest.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    missing = [row["artifact_path"] for row in rows if not row["exists"]]
    print(f"Wrote {out.relative_to(ROOT)} with {len(rows)} manifest rows")
    if missing:
        raise SystemExit(f"Missing manifest artifacts: {missing}")


if __name__ == "__main__":
    main()
