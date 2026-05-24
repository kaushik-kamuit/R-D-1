# IEEE Access Revision Handoff Notes

Branch: `codex/ieee-access-reviewer-fixes`

## What changed technically

- Fixed stale Figure 5 split references in the paper package and validator.
- Restored the IEEE decision-letter manuscript title: `Route-Aware Ride-Pooling Dispatch via Spatiotemporal Corridor Matching`.
- Fixed route-cache precedence so Yellow prefers `data/route_cache_yellow.db` over the empty legacy `data/route_cache.db`.
- Added reviewer evidence generation:
  - `scripts/run_reviewer_revision_evidence.py`
  - `scripts/run_stronger_dispatch_baselines.py`
  - `scripts/profile_osrm_live_latency.py`
  - `scripts/run_model_policy_diagnostic.py`
  - `scripts/run_validation_heuristic_selection.py`
  - `scripts/build_retained_density_sensitivity.py`
  - `scripts/run_dispatch_corridor_sensitivity.py`
  - `scripts/run_path_buffer_baseline.py` rerun at 1000 drivers with `--prefetch-missing`
  - `scripts/build_dispatch_policy_gap_summary.py`
  - `scripts/build_dispatch_uncertainty_summary.py`
  - `scripts/build_runtime_resource_summary.py`
  - `scripts/build_reviewer_response_matrix.py`
  - `scripts/audit_reviewer_response_traceability.py`
  - `scripts/build_revision_artifact_manifest.py`
  - `scripts/audit_revision_package.py`
- Added reviewer-facing result artifacts:
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
  - `results/osrm_live_latency_probe_raw.csv`
  - `results/stronger_dispatch_baselines.csv`
  - `results/model_policy_diagnostic.csv`
  - `results/model_policy_diagnostic_dataset.csv`
  - `results/validation_heuristic_selection.csv`
  - `results/validation_heuristic_selection_raw.csv`
  - `results/retained_density_sensitivity.csv`
  - `results/dispatch_corridor_sensitivity.csv`
  - `results/path_buffer_single_driver_summary.csv`
  - `results/path_buffer_dispatch_summary.csv`
  - `results/path_buffer_baseline_comparison.csv`
  - `results/path_buffer_baseline_config.json`
  - `results/dispatch_policy_gap_summary.csv`
  - `results/dispatch_uncertainty_summary.csv`
  - `results/runtime_resource_summary.csv`
  - `results/reviewer_response_matrix.csv`
  - `results/reviewer_response_traceability.csv`
  - `results/revision_artifact_manifest.csv`
  - `results/revision_package_audit.csv`
- Added `paper/response_to_reviewers_draft.md` mapping every reviewer comment to concern, response, and action.

## Manuscript additions

- Reframed novelty as route-aware candidate construction plus exact-time dispatch evaluation.
- Replaced cross-domain/public-domain wording with same-city service-type robustness.
- Added prior-work positioning table.
- Added external dataset audit table and expanded the checked artifact to separate rows for Chicago, Porto, Washington DC, NYC HVFHV/FHV, San Francisco, Los Angeles, Austin, Seattle, Toronto, Boston, Philadelphia, Dallas, and Houston.
- Added proxy role distribution table and threshold-sensitivity caveat.
- Added route-alternative overlap, eligibility-rule ablation, greedy-vs-optimal assignment, stronger baseline diagnostics, feature dictionary, model-policy diagnostic, cached runtime, live OSRM latency probe, and code/reproducibility section.
- Expanded `results/reviewer_feature_dictionary.csv` with `feature_family` so the 38-row detailed artifact maps directly to the manuscript feature-family table; validator checks family coverage and leakage status.
- Added March Yellow validation heuristic selection: fare-density is the validation-selected non-ML rule; feasible-count is reported as a conservative stronger April-best heuristic benchmark.
- Added a retained-density sensitivity artifact for Reviewer 2 comment 8. It summarizes Yellow/Green dispatch at 10%, 25%, and 100% of the fixed 25% retained rider pool and states that this is not a substitute for a raw re-extraction with different pre-sampling probabilities.
- Added cached dispatch-level corridor sensitivity for H3 resolution, k-ring width, and densification; non-primary H3 resolutions recompute sampled rider cells before indexing.
- Replaced the old 250-driver cached path-buffer baseline with a 1000-driver live-or-cached rerun. Dispatch path-buffer now reduces loss from $8.25 to $8.07 but remains below the matching-ball heuristic at $7.30.
- Added a seed-level dispatch policy-gap table/artifact for Reviewer 2's uncertainty comments. It records Yellow ML warm-up vs. cold-start at +$0.93/driver, Yellow ML warm-up vs. best heuristic at +$0.15/driver, and Green ML warm-up vs. best heuristic at +$0.27/driver; the manuscript states that retained-sample intervals collapse to point estimates and should not be read as broad population uncertainty.
- Added `results/dispatch_uncertainty_summary.csv`, a CI-width audit over headline and density-sweep dispatch metrics; all 245 checked seed-level intervals collapse under the retained-sample protocol.
- Corrected the runtime paragraph to match the expanded Yellow route cache: 1000 entries after the full path-buffer rerun, not the earlier smaller cache count.
- Corrected the cached end-to-end runtime table/text to match `results/end_to_end_runtime_profile.csv`: mean total 13.1 ms and max total 66.2 ms.
- Hardened `scripts/validate_paper_consistency.py` so the runtime table rows, OSRM latency prose, and route-cache entry count are checked directly against the current CSV artifacts.
- Extended the consistency validator to compare model-policy diagnostic rows, stronger dispatch-baseline prose, and path-buffer numbers directly against the current CSV artifacts.
- Added `results/runtime_resource_summary.csv` and manuscript/response text for the memory-footprint part of the runtime concern: 23.1 MB SQLite cache, 22.8 kB average route payload, and 0.13 MB traced Python allocation for a single cached lookup.
- Added a package audit that confirms review-facing artifacts are present and explicitly flags heavier regeneration artifacts that are not bundled locally: trained model, training dataset, and raw dispatch outcomes.
- Extended the package audit with a `handoff_action` column so missing model/dataset/raw-dispatch files are clearly marked as regeneration/release-asset work rather than blockers for the current reviewer-evidence package.
- Added `results/reviewer_response_matrix.csv`, a 38-row coverage matrix generated from the response draft for handoff into the IEEE response template.
- Added `results/reviewer_response_traceability.csv`, now an 80-row audit confirming response-matrix file references and manuscript labels resolve.
- Tightened the remaining response-draft actions so every reviewer-comment row now has at least one machine-checkable manuscript label, file, or artifact reference; no response-matrix rows are unreferenced.
- Hardened `scripts/validate_paper_consistency.py` to fail if any reviewer-response matrix row loses its concrete artifact/table/file reference.
- Added `results/revision_artifact_manifest.csv`, a machine-readable manifest mapping review-facing artifacts to generator/source scripts.
- Cleaned root README/reproducibility wording so external-domain claims consistently say same-city service-type, and fixed a non-ASCII `+/-1` encoding artifact in `REPRODUCIBILITY.md`.
- Cleaned the manuscript reproducibility paragraph so the release-tag/commit-hash item reads as final-package preparation rather than an inline manuscript TODO.
- Moderated production-dispatch, external-city, calibrated-profit, and ML-dominance claims.

## Current verification

Passed:

```powershell
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
python -m py_compile scripts\run_dispatch_artifact.py scripts\run_reviewer_revision_evidence.py scripts\run_stronger_dispatch_baselines.py scripts\profile_osrm_live_latency.py scripts\run_model_policy_diagnostic.py scripts\run_validation_heuristic_selection.py scripts\build_retained_density_sensitivity.py scripts\run_dispatch_corridor_sensitivity.py scripts\run_path_buffer_baseline.py scripts\build_dispatch_policy_gap_summary.py scripts\build_dispatch_uncertainty_summary.py scripts\build_runtime_resource_summary.py scripts\build_reviewer_response_matrix.py scripts\audit_reviewer_response_traceability.py scripts\build_revision_artifact_manifest.py scripts\audit_revision_package.py scripts\validate_paper_consistency.py
python scripts\validate_paper_consistency.py
python -m unittest discover -s tests
pdflatex -interaction=nonstopmode ieee_submission.tex
bibtex ieee_submission
pdflatex -interaction=nonstopmode ieee_submission.tex
pdflatex -interaction=nonstopmode ieee_submission.tex
```

The direct PDF build succeeds. The final LaTeX log has no undefined-reference, warning, error, overfull, or invalid-math lines after the title restoration plus latest manifest and documentation polish. `latexmk` itself is not usable on this machine because MiKTeX cannot find Perl, so the direct `pdflatex`/`bibtex` sequence was used. `git diff --check` reports only normal CRLF conversion warnings for this Windows checkout, not whitespace errors.

## Remaining packaging work

- Final formatting and copyediting.
- Create IEEE highlighted PDF from the revised manuscript.
- Convert or adapt `paper/response_to_reviewers_draft.md` into the IEEE response template.
- Mint a permanent GitHub release/tag and commit hash before final resubmission.
- Decide whether to bundle the trained model / training dataset / raw dispatch outcome files in a release asset or document regeneration-only access; `results/revision_package_audit.csv` lists these as regeneration artifacts, not review-facing checked-in CSVs.
- Decide whether to keep the old `paper_fig5_single_driver_mechanism.png` files as archived assets or remove them from the final package.
- No byline-change form is needed unless the author list changes.
