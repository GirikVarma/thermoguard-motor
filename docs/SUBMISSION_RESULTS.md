# Measured submission results

Run date: 25 October 2026. These are actual results from the exported experiment.

## Healthy signals: complete held-out profiles

| Component | Baseline MAE (C) | Neural ensemble MAE (C) | Ensemble RMSE (C) | P95 underestimation (C) | Upper coverage |
| --- | --- | --- | --- | --- | --- |
| Rotor magnet | 3.832 | 3.390 | 4.449 | 4.088 | 82.0% |
| Stator winding | 1.774 | 1.604 | 2.329 | 2.873 | 85.4% |
| Stator tooth | 1.565 | 1.436 | 2.009 | 2.338 | 84.5% |
| Stator yoke | 1.252 | 1.080 | 1.503 | 1.843 | 85.1% |

## Scenario summary

| Scenario | Mean baseline MAE (C) | Mean ensemble MAE (C) | Mean upper coverage |
| --- | --- | --- | --- |
| clean | 2.106 | 1.877 | 84.3% |
| dropout | 2.212 | 1.996 | 83.0% |
| combined | 2.321 | 2.088 | 81.0% |
| bias | 2.097 | 1.878 | 85.2% |
| stuck | 2.105 | 1.877 | 84.3% |

Metrics are macro-averaged over 15 whole test profiles, then across components for the scenario summary. Dropout averages coolant and q-axis voltage cases. Each event lasts 120 seconds at 45% of profile duration. Bias is a +10 C coolant ramp. Cold starts remain included.

The calibration target was an empirical 90% pointwise upper estimate on separate calibration data. Held-out coverage is lower; this is not a certified temperature bound.

The baseline is one clean-trained network and the robust estimator averages three fault-trained networks. Their comparison does not isolate fault training from ensembling, extra training data, or seed variation. A formal paper needs controlled ablations and additional grouped splits.

Full per-profile values and split IDs: results/evaluation.json. Checkpoint histories and weights: web/assets/model.json. Dataset checksum and provenance: data/manifests/audit.json.

## Implemented versus proposed

Implemented: causal features, deep ensemble, known-dropout training, held-out evaluation, empirical calibration, browser inference, export, and advisory replay.

Future work: full thermal-network dynamics, GRU comparisons, asymmetric loss, profile-level conformal bounds, independent control simulation, embedded hardware, and cross-motor tests. Earlier proposal files describe these broader goals.

## Verification

Seven Python protocol tests check profile isolation, feature causality, target exclusion, source preservation, silent-error masks, and model structure. A Node test executes the actual browser engine and compares it against Python on measured samples. Browser checks verify replay controls, sensor scenarios, component switching, benchmarks, exports, and the packaged standalone asset structure.

The local-server UI is browser-tested. Direct file-URL browser automation is blocked by the testing browser policy, so the standalone file was checked structurally rather than opened through that automation. Use the Python launcher if a browser blocks file-based workers.
