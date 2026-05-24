# Response to Reviewers Draft

Manuscript: Access-2026-17935, "Route-Aware Ride-Pooling Dispatch via Spatiotemporal Corridor Matching"

## Reviewer 1

### Comment 1
Concern: The method may look like a straightforward integration of H3, OSRM, and gradient-boosted trees rather than a novel methodological advance.

Response: We agree that the novelty should not be framed as inventing H3, OSRM alternatives, or ML ranking. The revised paper positions the contribution as route-aware candidate construction with exact post-retrieval eligibility and dispatch-first evaluation.

Action: Added Table `tab:prior_work_positioning`, rewrote the abstract/contributions, and clarified that ML is a residual scorer rather than the core novelty.

### Comment 2
Concern: The ML gain over the strongest heuristic is small.

Response: We agree and now make this the central interpretation rather than a weakness hidden in the results.

Action: Reframed the conclusion and added/updated Table `tab:dispatch_policy_gap` plus Figures `fig:single_driver_gain_comp` and `fig:single_driver_residual`; ML adds a modest residual edge of $0.15/driver in the primary Yellow sparse dispatch scenario.

### Comment 3
Concern: Long taxi trips as drivers and short trips as riders are an imperfect proxy for ride-pooling.

Response: We agree. The revised manuscript limits the proxy claim to controlled route-aware candidate construction, not live pooled-demand behavior.

Action: Added Table `tab:proxy_distribution`, `results/proxy_role_distribution_summary.csv`, `results/proxy_threshold_sensitivity.csv`, and stronger proxy-validity language.

### Comment 4
Concern: The rolling-horizon simulator is simpler than production dispatch.

Response: We agree. The simulator is now described as a low-latency route-choice layer with rider exclusivity, not a production dispatch platform.

Action: Expanded Algorithm `alg:dispatch`, the rolling-horizon description in `paper/ieee_submission.tex`, and the limitation section on repositioning, long-horizon assignment, and continued driver activity.

### Comment 5
Concern: Fixed scenario assumptions are not calibrated to real operations.

Response: We agree and keep all financial quantities as scenario-profit values.

Action: Strengthened Table `tab:scenario_assumptions`, Table `tab:economics_sensitivity`, and limitation wording; reiterated that reported values are not calibrated platform margins or forecasts.

### Comment 6
Concern: Baselines are too basic.

Response: We added a structured prior-work positioning table, reran the path-buffer comparator at the 1000-driver headline scale, and strengthened the heuristic baseline discussion. We also added cached-subset diagnostics for greedy nearest-route dispatch and single-rider batch bipartite assignment. Full RTV/global fleet optimization remains outside the current public-data scope.

Action: Added Table `tab:prior_work_positioning`, path-buffer comparison text, `results/stronger_dispatch_baselines.csv`, and clearer scope boundaries.

### Comment 7
Concern: 2015 taxi data may not represent current ride-pooling markets.

Response: We agree. The data are used as a public reproducible benchmark with exact OD/time/fare fields, not as a claim about current market behavior.

Action: Moderated proxy and conclusion language in `paper/ieee_submission.tex`, added the temporal split in Table `tab:data_split`, and tied current-market limitations to the external-data audit in Table `tab:external_data_audit`.

### Comment 8
Concern: Evaluation is only NYC Yellow/Green.

Response: We audited major public external-city candidates. Chicago is promising but privacy-rounded; Porto lacks comparable economics; Washington DC is too coarse for exact-window matching; and the San Francisco, Los Angeles, Austin, Seattle, Toronto, Boston, Philadelphia, Dallas, and Houston portal audit did not find comparable official trip-level taxi/TNC OD data.

Action: Added `tab:external_data_audit` and changed "cross-domain" claims to "same-city service-type" robustness.

### Comment 9
Concern: Residual ML gain is too small to justify complexity.

Response: We agree that the paper should not claim ML dominance.

Action: Reframed ML as optional residual ranking on top of route-aware retrieval; highlighted heuristic recovery and oracle headroom decomposition in Figures `fig:single_driver_gain_comp` and `fig:single_driver_residual`.

### Comment 10
Concern: Runtime excludes route retrieval and corridor construction.

Response: We added cached end-to-end profiling for route lookup, corridor construction, and candidate filtering/matching, a route-cache resource/memory-footprint summary, plus a tiny live public-OSRM latency probe. We explicitly state that public-server latency is not a production guarantee.

Action: Added Table `tab:end_to_end_runtime`, `results/end_to_end_runtime_profile.csv`, `results/runtime_resource_summary.csv`, and `results/osrm_live_latency_probe.csv`.

## Reviewer 2

### Comment 1
Concern: Placeholder IEEE metadata remains.

Response: The current manuscript source does not include placeholder publication metadata or DOI fields.

Action: Verified `paper/ieee_submission.tex` for placeholder publication and DOI strings and added this check to `scripts/validate_paper_consistency.py`.

### Comment 2
Concern: Abstract lacks a concise novelty statement.

Response: We revised the abstract to emphasize route-aware candidate construction plus exact-time dispatch evaluation rather than tool combination.

Action: Rewrote the abstract framing in `paper/ieee_submission.tex` to state the specific novelty as route-aware matching-ball retrieval plus exact-time dispatch evaluation over genuine OSRM alternatives.

### Comment 3
Concern: Alternative-route candidate-pool differences are asserted but not demonstrated early.

Response: We added route-cell overlap, candidate overlap, feasible-candidate overlap, and default-route comparison evidence.

Action: Added route-alternative overlap paragraph and `results/route_alternative_overlap_summary.csv`.

### Comment 4
Concern: Contributions are mainly system integration.

Response: We added an explicit comparison table against T-Share, shareability networks, dynamic assignment, rolling dispatch, path-buffer retrieval, and learning-based dispatch.

Action: Added Table `tab:prior_work_positioning`.

### Comment 5
Concern: Related work lacks direct technical comparison.

Response: We now explicitly state what is reused, what is contributed, and what is outside scope.

Action: Added Table `tab:prior_work_positioning` and revised related-work transition.

### Comment 6
Concern: "Cross-domain robustness" is overstated for Yellow/Green NYC.

Response: We agree.

Action: Renamed this claim to "same-city service-type robustness" throughout `paper/ieee_submission.tex` and added Table `tab:external_data_audit`.

### Comment 7
Concern: Driver/rider thresholds need justification.

Response: We added role distributions and threshold-sensitivity artifacts.

Action: Added Table `tab:proxy_distribution`, `results/proxy_role_distribution_summary.csv`, and `results/proxy_threshold_sensitivity.csv`.

### Comment 8
Concern: 25% rider pre-sampling needs justification and sensitivity.

Response: We clarify that 100% density means the full retained 25% sample and that density sweeps are fractions of that retained sample. We also added a retained-sample sensitivity artifact over 10%, 25%, and 100% of the retained rider pool, while explicitly noting that this does not replace a full raw-data rerun at different pre-sampling probabilities.

Action: Revised retained-sample semantics and added proxy audit outputs plus `scripts/build_retained_density_sensitivity.py` and `results/retained_density_sensitivity.csv`.

### Comment 9
Concern: Economic assumptions need evidence/sensitivity.

Response: We keep the assumptions as scenario values and avoid calibrated profitability claims.

Action: Strengthened scenario-assumption language and limitation wording; added an economic sensitivity table from `results/economics_sensitivity.csv`.

### Comment 10
Concern: H3 resolution, densification, and k-ring choices need justification.

Response: Existing single-driver H3 sensitivity is retained, and we added a cached dispatch-level corridor diagnostic varying H3 resolution, k-ring width, and densification. The diagnostic recomputes rider H3 cells when route resolution changes and is labeled as a bounded sensitivity probe.

Action: Added Table `tab:dispatch_corridor_sensitivity`, `scripts/run_dispatch_corridor_sensitivity.py`, and `results/dispatch_corridor_sensitivity.csv`.

### Comment 11
Concern: Pickup-and-drop-off eligibility may be too restrictive.

Response: We added an eligibility-rule ablation comparing pickup-only, drop-off-only, and pickup-and-drop-off retrieval.

Action: Added Table `tab:eligibility_ablation` and `results/eligibility_rule_ablation.csv`.

### Comment 12
Concern: Directionality and detour are not operationally defined.

Response: We added precise implementation details.

Action: Defined Shapely projection ordering, minimum downstream fraction, detour conversion, Manhattan factor, urban speed, and greedy multi-rider handling in Algorithm `alg:dispatch` and the matching-ball implementation text.

### Comment 13
Concern: Greedy fare-based seat assignment may bias results.

Response: We compared greedy assignment with exhaustive small-batch assignment on cached route cases.

Action: Added greedy-vs-optimal paragraph and `results/greedy_vs_optimal_assignment.csv`.

### Comment 14
Concern: Profit formula needs clarification.

Response: The revised paper states the exact scenario-profit formula and what is excluded.

Action: Clarified scenario profit in the route-ranking formula and Table `tab:scenario_assumptions`, with limitations around original driver fare, behavioral acceptance, waiting, and opportunity costs.

### Comment 15
Concern: Strongest heuristic selection may cause test-set selection bias.

Response: We added a March 2015 Yellow validation probe to pre-select the non-ML heuristic before April test interpretation. The validation probe selects fare-density. On the April primary dispatch test, feasible-rider count is stronger, so the revised paper reports feasible-count as a conservative upper heuristic benchmark and separately reports ML's gain over the validation-selected fare-density rule.

Action: Added `scripts/run_validation_heuristic_selection.py`, `results/validation_heuristic_selection.csv`, and `results/validation_heuristic_selection_raw.csv`; revised the Route-Ranking Policies and Primary Yellow Sparse Dispatch sections.

### Comment 16
Concern: Algorithm 1 is too high level.

Response: We expanded operational text around retrieval, cache usage, exact filtering, directionality, detour, tie-breaking, and seat assignment.

Action: Added implementation details in Algorithm `alg:dispatch` and the matching-ball section.

### Comment 17
Concern: Simulator lacks repositioning/global assignment; add stronger dispatch baselines.

Response: We agree that full global assignment is outside the current implementation. We added stronger scope boundaries, kept path-buffer as a bounded baseline, and added cached-subset greedy nearest-route and single-rider batch bipartite diagnostics.

Action: Added `scripts/run_stronger_dispatch_baselines.py`, `results/stronger_dispatch_baselines.csv`, moderated operational claims, and clarified that the simulator is not a production dispatch optimizer.

### Comment 18
Concern: Dispatch experiment size/statistics need more evidence.

Response: We now add an explicit dispatch policy-gap summary for the 1000-driver, five-seed headline setup and state that the retained-sample seed intervals collapse to point estimates because the simulator is nearly deterministic. We also added a CI-width audit over the headline and density-sweep dispatch metrics to make that collapse explicit. We therefore present the gaps as repeat-run policy comparisons rather than overstated inferential confidence intervals.

Action: Added `scripts/build_dispatch_policy_gap_summary.py`, `results/dispatch_policy_gap_summary.csv`, `scripts/build_dispatch_uncertainty_summary.py`, `results/dispatch_uncertainty_summary.csv`, and Table `tab:dispatch_policy_gap`; clarified the statistical interpretation in the primary dispatch section.

### Comment 19
Concern: The 38 features are not listed.

Response: We added a feature dictionary table with leakage status.

Action: Added Table `tab:feature_dictionary` and `results/reviewer_feature_dictionary.csv`.

### Comment 20
Concern: Path-buffer baseline uses a smaller subset.

Response: We reran the path-buffer baseline at the same 1000-driver scale as the primary Yellow dispatch headline, using live-or-cached OSRM routes, the same 5-minute exact request window, and the same 4-minute detour rule. The path-buffer comparator improves over cold-start but remains weaker than the matching-ball heuristic in both dispatch and controlled single-driver settings.

Action: Regenerated `results/path_buffer_single_driver_summary.csv`, `results/path_buffer_dispatch_summary.csv`, `results/path_buffer_baseline_comparison.csv`, and `results/path_buffer_baseline_config.json`; revised the path-buffer paragraph.

### Comment 21
Concern: Green is not a true public-domain shift.

Response: We agree.

Action: Replaced "public-domain/cross-domain" wording with "same-city service-type" wording in `paper/ieee_submission.tex`, grounded the Green result in Table `tab:domain_transfer`, and added the scope boundary in Table `tab:external_data_audit`.

### Comment 22
Concern: Dispatch uncertainty is weaker than single-driver uncertainty.

Response: The paper now clarifies that dispatch intervals are repeat-run dispersion under retained-sample seeds and often collapse because the simulator is near-deterministic. The dispatch layer is therefore paired with the larger driver-level bootstrap study, while the dispatch table reports the exact seed-level policy gaps for Yellow and Green. A separate CI-width audit records the collapsed intervals across the headline and density-sweep metrics.

Action: Added the dispatch policy-gap artifact/table, added `results/dispatch_uncertainty_summary.csv`, and clarified that these are point estimates under the retained-sample protocol, not broad population uncertainty intervals.

### Comment 23
Concern: LightGBM selection needs stronger justification versus MLP/LambdaRank.

Response: We now state that MLP slightly improves regression fit and LambdaRank improves rank-1 accuracy, but LightGBM was chosen for balanced calibration/ranking. We also added a cached held-out route-policy diagnostic across model families to check whether predictive metrics translate into route-choice profit.

Action: Expanded model-support interpretation and added `scripts/run_model_policy_diagnostic.py` plus `results/model_policy_diagnostic.csv`.

### Comment 24
Concern: Feature importance suggests ML mainly learns demand density.

Response: We agree and now say so directly.

Action: Added Table `tab:model_ablation` and reframed ML as demand-aware residual scoring.

### Comment 25
Concern: Sensitivity is incomplete at dispatch level.

Response: Dispatch-level window and detour sensitivity are retained, and we added a cached dispatch-level H3/corridor diagnostic that varies H3 resolution, k-ring width, and densification on the Yellow 10% scenario. The diagnostic recomputes rider H3 cells when route resolution changes and is explicitly labeled as a 50-driver sensitivity probe rather than a replacement for the 1000-driver headline experiment.

Action: Added `scripts/run_dispatch_corridor_sensitivity.py`, `results/dispatch_corridor_sensitivity.csv`, and Table `tab:dispatch_corridor_sensitivity` in the Sensitivity and Runtime section.

### Comment 26
Concern: Runtime excludes route-fetch latency/cache behavior.

Response: We added cached route-scoring stage timing, cache hit/miss counts, a route-cache resource/memory-footprint summary, and a tiny public-OSRM route-fetch latency probe, with clear caveats about public-server latency.

Action: Added Table `tab:end_to_end_runtime`, `scripts/build_runtime_resource_summary.py`, `results/runtime_resource_summary.csv`, `scripts/profile_osrm_live_latency.py`, and OSRM latency probe result files.

### Comment 27
Concern: Discussion overstates operational usefulness.

Response: We moderated the conclusion and discussion.

Action: Removed production-dispatch and calibrated-profitability implications from the Discussion/Conclusion and reinforced the limits in Table `tab:scenario_assumptions`.

### Comment 28
Concern: Code availability and reproducibility details need correction.

Response: We added reviewer-evidence scripts, result anchors to the paper README, a machine-readable artifact manifest, and a code/reproducibility section with the corrected GitHub URL.

Action: Updated `paper/README.md`, added `scripts/run_reviewer_revision_evidence.py`, added `scripts/build_revision_artifact_manifest.py`, added validation checks for new reviewer artifacts, and added a Code and Reproducibility section to the manuscript.
