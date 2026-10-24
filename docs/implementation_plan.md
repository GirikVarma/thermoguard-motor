# Implementation plan

**Planning basis:** approximately 12 academic weeks, with a working estimation/replay prototype targeted by week 8. The schedule is a proposed effort estimate, not a delivery commitment. The same person can combine roles; a three-person team can divide electrical modeling, machine learning, and software/evaluation.

## 1. Planned software organization

The following structure describes future implementation. The modules and commands are not yet implemented.

| Planned path | Responsibility |
| --- | --- |
| data/raw/ | Locally acquired, unchanged source archive |
| data/manifests/ | Checksums, schema, license record, profile splits |
| src/data.py | Causal features, normalization, profile-safe sequences |
| src/faults.py | Deterministic dropout, bias, and stuck-value events |
| src/models/ | Dynamic regression, GRU, and thermal neural models |
| src/train.py | Seeded training, checkpoints, validation selection |
| src/calibrate.py | Profile-level ensemble-bound calibration |
| src/evaluate.py | Clean/fault metrics and profile-bootstrap intervals |
| src/supervisor.py | Illustrative advisory torque multiplier |
| src/plant.py | Optional independent thermal/control simulator |
| app.py | Recorded-data replay dashboard |
| configs/ | Frozen model, split, and failure-suite settings |
| tests/ | Leakage, causality, fault, and calibration checks |
| outputs/ | Results, figures, manifests, and experiment logs |

## Recommended tools

Use Python, PyTorch, NumPy, pandas, scikit-learn, matplotlib, and Streamlit. Add pytest for meaningful data and state-transition tests. Pin versions after a successful installation and smoke test on the actual host. These packages are recommendations; this proposal does not assume they are all installed.

A modern laptop with approximately 16 GB RAM is a reasonable starting point. A GPU is helpful for the ensemble but should be optional for small models. Begin with one target and a few training profiles, then expand to four targets and full profiles. Measure resource consumption before increasing model size. No EV, traction inverter, or high-voltage hardware is required for the core recorded-data study.

## Run records

Every experiment should retain the source checksum, git revision, exact profile split, preprocessing statistics, fault schedule, random seed, model settings, checkpoint selection rule, and output metrics. Keep source data out of version control unless redistribution is explicitly permitted. Use the same event manifest for every model in a paired comparison.

<!-- pagebreak -->

# 2. Work packages and weekly milestones

| Week | Work package | Reviewable completion evidence |
| --- | --- | --- |
| 1 | Acquire and audit data; verify license and literature | Dataset card, units, checksum, profile inventory, source matrix |
| 2 | Freeze grouped splits; implement causal preprocessing | Split manifest and passing leakage/causality checks |
| 3 | Train dynamic regression and a small GRU | Clean per-profile metrics and reproducible checkpoints |
| 4 | Implement and validate thermal neural baseline | Documented thermal update, stable full-profile rollouts |
| 5 | Add missing-input masks and causal fallback | Deterministic F1-F3 events and B2/B3 comparison |
| 6 | Train ensemble and calibrate upper bounds | Calibration record, coverage and interval-width plots |
| 7 | Run frozen test suite and bias/stuck stress tests | Complete metrics, seeds, uncertainty, worst-case traces |
| 8 | Build replay dashboard | A full demonstration with logged settings and exportable figures |
| 9 | Optional independent plant and derating study | Clearly labeled simulated control-effect results |
| 10 | Repeat only unresolved experiments; interpret outcomes | Locked result tables, ablations, limitations |
| 11 | Write research paper using measured results | Manuscript, bibliography, methods and data statement |
| 12 | Prepare presentation and reproduce a clean run | Slide deck, demonstration script, handover instructions |

## Stage gates

**Gate A, end of week 2:** data is accessible, units are understood, and profile isolation is proven. If access fails, switch to the authors' documented acquisition route or a separately licensed source; do not silently replace measured data with synthetic samples.

**Gate B, end of week 4:** clean temperature estimates are reproducible. If the thermal model is unstable or too costly, use the GRU as the primary estimator and retain physics-guided work as an extension. Explain the scope change in the paper.

**Gate C, end of week 7:** test metrics and known failure cases are available. If fault robustness does not improve, retain the benchmark and investigate observability, rather than inventing gains or tuning to the final test set.

**Gate D, end of week 8:** a reviewer can replay an unseen profile, trigger a dropout, and inspect estimates without a live model-training session.

**Gate E, week 9:** add the control simulator only if the core estimation study is complete. A polished estimation project is sufficient; the optional control study must not displace the main evidence.

<!-- pagebreak -->

# 3. Experiment matrix and implementation details

## Minimum model comparison

| Model | Missing-input exposure | Main purpose |
| --- | --- | --- |
| B0: dynamic linear regression | Same causal fallback at test time | Simple temporal baseline |
| B1: GRU | Clean training initially | Standard deep sequence baseline |
| B2: thermal neural network | Clean training | Physical-structure baseline |
| B3: same network plus masks and age | Clean and masked training | Isolate fault-training benefit |
| B4: B3 with underestimation penalty | Same fault training | Isolate asymmetric-loss effect |

The ensemble is a calibration layer over the selected robust model, not a replacement for the single-model comparisons. Select B3 or B4 on validation results before final testing. Keep B2/B3 backbones identical except for the features needed to represent missingness. Include a mask-without-fault-training ablation if the apparent benefit could come from added parameters.

## Event generation

Pre-register event durations of 5, 30, and 120 seconds. At 2 Hz these correspond to 10, 60, and 240 samples if the acquisition audit confirms uninterrupted 0.5-second sampling. Place events away from profile boundaries and record the duration actually available. Train on selected durations and combinations; reserve one harder duration/combination for a declared generalization stress test.

For stuck values, replace future observations with the last valid sample at onset. For a bias ramp, add a declared ramp to the chosen input channel. Suggested coolant stress magnitudes are +5 and -5 degrees Celsius over 120 seconds, with a separate +10/-10-degree severity test. These values are experimental assumptions. Do not corrupt target labels or supply an oracle mask for these unreported errors.

## Recovery and cold-start evaluation

When a channel returns, record the temperature-error trajectory and compare it with the same model's clean replay. Report a recovery curve; define any recovery-time threshold using validation data before testing. Evaluate cold starts with boundary-based initialization. Report an instrumented initial-state experiment separately if performed.

## Statistical comparisons

Calculate paired model differences using the same profiles and event schedules. Bootstrap complete test profiles, not individual timestamps, to obtain intervals for aggregate differences. Keep training-seed variation separate. If a session contains multiple related profiles or repeats, group by the broader session identifier when available. Operating-profile holdout on one motor supports same-platform generalization only.

<!-- pagebreak -->

# 4. Quality checks, risks, and completion criteria

## Meaningful implementation checks

- Assert that training, validation, calibration, and test profile IDs are disjoint.
- Confirm that target-temperature columns and measured torque cannot enter primary input features.
- Verify that altering a future sample cannot change earlier model predictions.
- Confirm that window extraction never spans two profiles and recurrent state resets at boundaries.
- Ensure generated dropout events leave the reference labels unchanged and are repeatable from a seed.
- Check that an unreported bias/stuck event does not expose its true onset or mask to the estimator.
- Test heat-flow sign conventions, positive thermal parameters, and stable long rollouts.
- Confirm that upper-bound calibration uses calibration profiles only and handles insufficient sample counts explicitly.
- Verify that replay remains advisory and does not report counterfactual cooling as an observed outcome.

## Risk register

| Risk | Response |
| --- | --- |
| Dataset access or unclear license | Resolve access and terms before implementation; record source version |
| Strong similarity to existing research | Narrow the contribution and compare the closest methods explicitly |
| Unknown initial temperatures | Separate cold-start results and expose wider uncertainty |
| Model exploits unavailable inputs | Enforce an input allowlist and test it automatically |
| Narrow bounds with missed hot events | Evaluate underestimation and coverage together; report failures |
| Long intervals make advice unusable | Report width and derating cost, not coverage alone |
| Optional simulator dominates schedule | Freeze the estimation scope first; keep control as an extension |

## Definition of a completed core project

The project is complete when another student can acquire the permitted data, reproduce the split and baseline results, replay a held-out fault scenario, and regenerate the main tables and figures. The report must include clean performance, F1-F3 robustness, unreported-error stress tests, uncertainty behavior, and representative worst cases.

The proposed 15% underestimation-reduction and 10% clean-error-tolerance targets guide interpretation; failing a target does not justify hiding results. Inference timing must name the tested hardware and batch size. Keep automotive certification, fleet deployment, measured energy savings, and prevented motor damage out of the claims unless independently supported.

## First implementation session

Acquire the dataset, record its license and checksum, inspect profile lengths and temperature ranges, freeze the input allowlist, create the grouped split, and run the simple dynamic baseline. Review those results before selecting neural-model capacity or thresholds. This sequence makes the next decision evidence-based.

<!-- pagebreak -->

# 5. Research paper and presentation plan

## Proposed research-paper structure

1. **Abstract:** problem, proposed method, dataset, and measured outcomes after experiments.
2. **Introduction:** thermal monitoring problem, sensor availability, and precise contribution.
3. **Related work:** recurrent estimators, thermal neural networks, hybrid models, and robustness studies.
4. **System and data:** input availability, target definition, provenance, grouped split, and initial conditions.
5. **Method:** thermal dynamics, missing-input representation, training loss, and calibration.
6. **Experimental design:** baselines, fault generation, metrics, seed policy, and paired comparisons.
7. **Results:** clean performance, dropout robustness, bias/stuck stress, intervals, latency, and ablations.
8. **Discussion:** observability, uncertainty failures, same-motor limits, and optional control simulation.
9. **Conclusion:** supported findings and specific remaining work.
10. **References and reproducibility statement:** source versions, code availability, and data terms.

Do not fill the results section with estimated improvements. Until experiments run, label all result tables as planned schemas without numerical findings.

## Planned figures and tables

- Motor component schematic and estimator architecture.
- Per-profile data-split summary and an input-availability table.
- Representative temperature traces with dropout intervals and upper bounds.
- Underestimation versus dropout duration, with per-profile variation.
- Coverage-versus-width and recovery plots, including failure examples.
- Model comparison and ablation tables.
- A control-performance table only if the separate simulator is completed.

## Suggested 12-slide presentation

Use one slide each for: the electrical problem; the research question; existing work and proposed contribution; dataset and signals; thermal equation and model; failure scenarios; evaluation design; actual baseline results; robustness and uncertainty findings; the replay demonstration; limitations and optional control study; conclusions and references. Before experiments, use a proposal deck and replace result slides with planned analyses.

## Evidence ledger and handover

Tag every claim as a source-backed fact, a proposed design choice, a measured project result, or a simulation result. Preserve those distinctions in the paper, slide captions, and dashboard. The final handover should include environment instructions, data-acquisition steps, configuration files, a complete example run, model checkpoints where redistribution is permitted, and a short demo script.

## Immediate next milestone

The first review should contain the data audit, exact profile split, baseline error plots, and the final frozen fault protocol. Those artifacts will determine whether the physics-guided model and uncertainty layer add enough value for the remaining implementation effort.
