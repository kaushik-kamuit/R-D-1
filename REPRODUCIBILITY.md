# Reproducibility Guide

This repository is packaged as a realism-first research artifact for route-aware ride-pooling evaluation on NYC TLC 2015 taxi data, with both a controlled single-driver study and a rolling-horizon dispatch study.

## Primary scenario

The manuscript and validator are anchored to this headline configuration:

- retained rider pre-sample: `25%`
- retained-sample density sweep: `100%, 75%, 50%, 25%, 10%`
- exact request window: `5 minutes`
- index lookup: `15-minute bins` with `+/-1` adjacent bins
- max detour: `4 minutes`
- seats: `3`
- platform share: `0.50`
- cost per mile: `$0.67`
- speed proxy: `40 km/h`

`100%` means the full retained `25%` rider pool, not full city demand.

## Main artifact outputs

- `results/realism_primary_summary.csv`: primary 5-minute density sweep
- `results/paper_primary_summary.csv`: single-row headline paper anchor
- `results/window_sensitivity.csv`: request-window sensitivity grid
- `results/detour_sensitivity.csv`: detour sensitivity at 10% density
- `results/strong_baseline_comparison.csv`: strongest non-ML heuristic comparison
- `results/temporal_generalization.csv`: Jan--Feb to Mar temporal holdout metrics
- `results/h3_corridor_sensitivity.csv`: matching-ball geometry sensitivity
- `results/economics_sensitivity.csv`: economics sensitivity at 10% density
- `results/runtime_profile.csv`: per-driver compute-time profile
- `results/scenario_assumptions.csv`: publication-facing scenario assumptions
- `results/strategy_gap_results.csv`: paired policy-gap statistics
- `results/strategy_gap_route_breakdown.csv`: route-length breakdown of paired gaps
- `results/model_comparison.csv`: model-family comparison
- `results/ablation_results.csv`: feature ablation study
- `results/plots/paper_fig*.png`: publication-facing figures
- `results/dispatch_yellow_primary.csv`: primary dispatch summary on NYC Yellow
- `results/dispatch_green_primary.csv`: same-city service-type robustness dispatch summary on NYC Green when available
- `results/domain_transfer_summary.csv`: Yellow-vs-Green dispatch comparison
- `results/domain_temporal_generalization.csv`: per-domain temporal validation metrics
- `results/dispatch_density_summary.csv`: dispatch density sweep
- `results/dispatch_service_wait_summary.csv`: dispatch service-rate and wait-time summary
- `results/prior_work_positioning.csv`: reviewer-facing novelty/related-work positioning table
- `results/external_dataset_audit.csv`: major public external-city data audit
- `results/proxy_role_distribution_summary.csv`: driver/rider proxy retained-count and distance summary
- `results/proxy_threshold_sensitivity.csv`: observable threshold-sensitivity audit from retained files
- `results/reviewer_feature_dictionary.csv`: 38-feature dictionary with manuscript family, source, availability, aggregation window, and leakage status
- `results/route_alternative_overlap_summary.csv`: candidate-pool overlap across OSRM alternatives
- `results/eligibility_rule_ablation.csv`: pickup-only/drop-off-only/pickup-and-drop-off eligibility comparison
- `results/greedy_vs_optimal_assignment.csv`: greedy seat-fill versus exhaustive small-batch assignment
- `results/end_to_end_runtime_profile.csv`: cached route lookup, corridor construction, filtering, and matching timings
- `results/osrm_live_latency_probe.csv`: tiny live public-OSRM latency probe
- `results/stronger_dispatch_baselines.csv`: cached nearest-route and batch bipartite diagnostics
- `results/model_policy_diagnostic.csv`: cached model-family route-policy diagnostic
- `results/validation_heuristic_selection.csv`: March Yellow validation probe used to pre-select the deployable non-ML heuristic before April interpretation
- `results/dispatch_corridor_sensitivity.csv`: cached dispatch-level H3/k-ring/densification diagnostic
- `results/path_buffer_baseline_comparison.csv`: 1000-driver live-or-cached path-buffer comparator against cold-start and matching-ball heuristics
- `results/dispatch_uncertainty_summary.csv`: dispatch CI-width audit for headline and density-sweep metrics
- `results/runtime_resource_summary.csv`: route-cache storage and single-lookup memory-footprint summary
- `results/reviewer_response_matrix.csv`: one-row-per-comment response coverage matrix
- `results/reviewer_response_traceability.csv`: response-matrix artifact and manuscript-label traceability audit
- `results/revision_artifact_manifest.csv`: machine-readable mapping from review-facing artifacts to generator/source scripts
- `results/revision_package_audit.csv`: audit of review-facing artifacts versus heavier regeneration artifacts

Legacy optimistic outputs are archived under `artifacts/legacy_optimistic_45min/`.

## Environment

Install dependencies with:

```powershell
python -m pip install -r requirements.txt
```

Core packages include:

- `pandas`, `pyarrow`
- `h3`, `shapely`
- `lightgbm`, `xgboost`, `scikit-learn`, `scipy`
- `matplotlib`, `seaborn`
- `requests`, `python-dotenv`, `joblib`, `tqdm`

## End-to-end pipeline

The top-level rebuild command is:

```powershell
python run_all.py
```

This runs:

1. `scripts/run_realism_artifact.py` for the controlled single-driver study
2. `scripts/run_dispatch_artifact.py` for the dispatch study and same-city service-type robustness

The single-driver artifact:

1. archives the earlier optimistic 45-minute artifact
2. rebuilds the 5-minute exact-window training dataset
3. retrains the LightGBM model and comparison baselines
4. runs the main density sweep and stronger-baseline comparisons
5. runs request-window, detour, H3, and economics sensitivity experiments
6. regenerates summaries, figures, and the paper validator outputs

The dispatch artifact:

1. reuses the realism-first timing and route-ranking stack
2. runs 60-second rolling dispatch batches
3. compares cold-start, the strongest heuristic, ML warm-up, and oracle-style upper bounds
4. writes dispatch summaries for Yellow primary runs and Green same-city service-type robustness when available

Useful shortcuts:

```powershell
python run_all.py --skip-dataset --skip-train
python run_all.py --dispatch-only --sample 1000 --seeds 3
python run_all.py --single-driver-only
python scripts\run_dispatch_artifact.py --sample 1000 --seeds 3 --primary-only
python run_all.py --sample 5000 --seeds 5
python scripts\summarize_realism_results.py
python scripts\analyze_strategy_gaps.py
python scripts\run_reviewer_revision_evidence.py --sample 100
python scripts\run_stronger_dispatch_baselines.py --sample 100 --density-pct 10
python scripts\profile_osrm_live_latency.py --sample 5
python scripts\run_model_policy_diagnostic.py --sample 140 --density-pct 10
python scripts\run_validation_heuristic_selection.py --sample 30 --density-pct 10
python scripts\build_retained_density_sensitivity.py
python scripts\run_dispatch_corridor_sensitivity.py --sample 50 --seeds 1
python scripts\run_path_buffer_baseline.py --sample 1000 --seeds 5 --prefetch-missing
python scripts\build_dispatch_policy_gap_summary.py
python scripts\build_dispatch_uncertainty_summary.py
python scripts\build_runtime_resource_summary.py
python scripts\build_reviewer_response_matrix.py
python scripts\audit_reviewer_response_traceability.py
python scripts\build_revision_artifact_manifest.py
python scripts\audit_revision_package.py
python visualizations\plot_paper_figures.py
python scripts\validate_paper_consistency.py
```

Dispatch summary files include `driver_sample_size` and `n_seeds`. Small smoke runs are useful for sanity checks, but they should not be promoted into the manuscript without rerunning the full target configuration.

## Paper-facing claims and their source files

- Primary density response:
  - `results/realism_primary_summary.csv`
  - `results/density_results.csv`
- Request-window and detour sensitivity:
  - `results/window_sensitivity.csv`
  - `results/detour_sensitivity.csv`
- Strongest non-ML heuristic comparison:
  - `results/strong_baseline_comparison.csv`
- Temporal model selection:
  - `results/temporal_generalization.csv`
- Matching-ball geometry and economics sensitivity:
  - `results/h3_corridor_sensitivity.csv`
  - `results/economics_sensitivity.csv`
- Runtime profile:
  - `results/runtime_profile.csv`
- Dispatch summaries:
  - `results/dispatch_yellow_primary.csv`
  - `results/dispatch_green_primary.csv`
  - `results/domain_transfer_summary.csv`
  - `results/dispatch_density_summary.csv`
  - `results/dispatch_service_wait_summary.csv`
- Direct ML vs heuristic comparison:
  - `results/strategy_gap_results.csv`
  - `results/strategy_gap_route_breakdown.csv`
  - `results/strategy_gap_summary.txt`
- Model fit and feature ablation:
  - `results/model_comparison.csv`
  - `results/ablation_results.csv`
- Publication figures:
  - `results/plots/paper_fig*.png`
- Reviewer-response diagnostics:
  - `results/prior_work_positioning.csv`
  - `results/external_dataset_audit.csv`
  - `results/proxy_role_distribution_summary.csv`
  - `results/proxy_threshold_sensitivity.csv`
  - `results/reviewer_feature_dictionary.csv`
  - `results/route_alternative_overlap_summary.csv`
  - `results/eligibility_rule_ablation.csv`
  - `results/greedy_vs_optimal_assignment.csv`
  - `results/end_to_end_runtime_profile.csv`
  - `results/osrm_live_latency_probe.csv`
  - `results/stronger_dispatch_baselines.csv`
  - `results/model_policy_diagnostic.csv`
  - `results/validation_heuristic_selection.csv`
  - `results/dispatch_corridor_sensitivity.csv`
  - `results/path_buffer_single_driver_summary.csv`
  - `results/path_buffer_dispatch_summary.csv`
  - `results/path_buffer_baseline_comparison.csv`
  - `results/dispatch_uncertainty_summary.csv`
  - `results/runtime_resource_summary.csv`
  - `results/reviewer_response_matrix.csv`
  - `results/reviewer_response_traceability.csv`
  - `results/revision_artifact_manifest.csv`
  - `results/revision_package_audit.csv`

## Paper sources

The standalone IEEE-style manuscript source is under `paper/`:

- `paper/ieee_submission.tex`
- `paper/references.bib`
- `paper/README.md`

The validator checks that the manuscript discloses:

- the retained `25%` rider pre-sample
- the `5-minute exact request window`
- the `15-minute` index bins
- the oracle scope `within the evaluated route set`
- scenario-profit wording rather than calibrated-margin wording

Run the validator with:

```powershell
python scripts\validate_paper_consistency.py
```
