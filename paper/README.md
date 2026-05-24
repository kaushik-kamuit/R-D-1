# Paper Package

This directory contains the standalone IEEE journal-style manuscript package for the dispatch-first, realism-aware NYC route-selection study.

## Files

- `ieee_submission.tex`: main manuscript source
- `references.bib`: bibliography
- `figures/`: local figure assets used by the paper

## Figures referenced by the manuscript

- `figures/paper_fig1_dispatch_architecture_v2.png`
- `figures/paper_fig2_matching_ball_mechanism.png`
- `figures/paper_fig3_dispatch_density.png`
- `figures/paper_fig5a_gain_composition.png`
- `figures/paper_fig5b_residual_ml_lift.png`
- `figures/paper_fig6_model_support.png`
- `figures/paper_fig7_sensitivity.png`

Supporting locked source assets that should not be replaced accidentally:

- `figures/paper_fig1_dispatch_architecture_source.png`: canonical architecture diagram source
- `figures/paper_fig2a_corridor_map.jpg`: mandatory corridor-map source for Figure 2(a)

Refresh publication figures from the repo root with:

```powershell
python visualizations\plot_paper_figures.py
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
python scripts\validate_paper_consistency.py
```

## Overleaf

Upload the full contents of `paper/` to a new Overleaf project. No parent-directory paths are required.

That folder contains:

- `ieee_submission.tex`
- `references.bib`
- `figures/`

## Result anchors

The manuscript narrative is anchored to the dispatch-first and realism-first result files under `../results/`, especially:

- `../results/dispatch_yellow_primary.csv`
- `../results/dispatch_green_primary.csv`
- `../results/dispatch_density_summary.csv`
- `../results/dispatch_service_wait_summary.csv`
- `../results/dispatch_window_sensitivity.csv`
- `../results/dispatch_detour_sensitivity.csv`
- `../results/domain_transfer_summary.csv`
- `../results/domain_temporal_generalization.csv`
- `../results/realism_primary_summary.csv`
- `../results/paper_primary_summary.csv`
- `../results/strong_baseline_comparison.csv`
- `../results/strategy_gap_results.csv`
- `../results/route_gain_decomposition_summary.csv`
- `../results/ml_gap_comparison_summary.csv`
- `../results/model_comparison.csv`
- `../results/ablation_results.csv`
- `../results/h3_corridor_sensitivity.csv`
- `../results/economics_sensitivity.csv`
- `../results/runtime_profile.csv`
- `../results/prior_work_positioning.csv`
- `../results/external_dataset_audit.csv`
- `../results/proxy_role_distribution_summary.csv`
- `../results/proxy_threshold_sensitivity.csv`
- `../results/reviewer_feature_dictionary.csv`
- `../results/route_alternative_overlap_summary.csv`
- `../results/eligibility_rule_ablation.csv`
- `../results/greedy_vs_optimal_assignment.csv`
- `../results/end_to_end_runtime_profile.csv`
- `../results/stronger_dispatch_baselines.csv`
- `../results/osrm_live_latency_probe.csv`
- `../results/osrm_live_latency_probe_raw.csv`
- `../results/model_policy_diagnostic.csv`
- `../results/model_policy_diagnostic_dataset.csv`
- `../results/validation_heuristic_selection.csv`
- `../results/validation_heuristic_selection_raw.csv`
- `../results/dispatch_corridor_sensitivity.csv`
- `../results/path_buffer_single_driver_summary.csv`
- `../results/path_buffer_dispatch_summary.csv`
- `../results/path_buffer_baseline_comparison.csv`
- `../results/path_buffer_baseline_config.json`
- `../results/dispatch_uncertainty_summary.csv`
- `../results/runtime_resource_summary.csv`
- `../results/reviewer_response_matrix.csv`
- `../results/reviewer_response_traceability.csv`
- `../results/revision_artifact_manifest.csv`
- `../results/revision_package_audit.csv`

The paper is organized so that rolling dispatch is the main system-level evidence and the larger single-driver study is controlled secondary evidence.

## Compile

Compile from the `paper/` directory with a standard LaTeX IEEE toolchain, for example:

```powershell
latexmk -pdf ieee_submission.tex
```

If `latexmk` is unavailable, run:

```powershell
pdflatex ieee_submission.tex
bibtex ieee_submission
pdflatex ieee_submission.tex
pdflatex ieee_submission.tex
```
