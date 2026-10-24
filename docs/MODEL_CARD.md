# ThermoGuard Motor: submission model card

## Actual architecture

Each model has 49 inputs, ReLU hidden layers of 96 and 64 units, and four linear outputs: **11,268 parameters**. Three independently seeded fault-trained models form the displayed ensemble. One clean-trained model is the baseline. Outputs are temperature rise over ambient for rotor magnet, winding, tooth, and yoke.

Inputs: i_d, i_q, u_d, u_q, motor speed, coolant temperature, and ambient temperature. Features add current-squared, absolute speed, an absolute d-q power proxy, causal histories with 10/60/300/900 s time constants, missingness masks, measurement ages, and elapsed time. No measured target temperature or torque enters prediction.

This is a physics-inspired temporal-feature network. It does not enforce the full heat-balance/learned-capacitance architecture from the original proposal.

## Actual training

Measured Paderborn data contains 69 profiles and 1,330,816 rows; ingestion detected no missing values. Every fourth row provides 2 s thermal samples. Split by whole profile: 34 train / 7 validation / 13 calibration / 15 test. The manifests list IDs and a raw CSV SHA-256 checksum.

Normalization and fallback medians use training data only. History resets between profiles. Training selects at most 1,200 evenly spaced points per profile/variant after constructing full causal histories. The baseline sees clean inputs. Robust models see clean data and two dropout variants per training profile. Missing inputs get a mask, age, a 20 s last-valid hold, and then a training-derived fallback.

AdamW minimizes squared regression error. Validation selects the checkpoint, with a 65-epoch maximum and patience of ten epochs. Seeds: baseline 7, robust 11/23/37. Both model types use the same clean/fault validation suite. Test data does not select the weights. Training histories are in web/assets/model.json.

## Upper estimates

For each component, the upper estimate is the ensemble mean plus a calibration multiplier times max(ensemble standard deviation, 2 C). The multiplier is the empirical 90th percentile of positive standardized residuals from profile-balanced samples on independent calibration profiles, replayed clean and under coolant, q-voltage, and combined dropouts.

This is empirical pointwise calibration, not the original proposal's profile-level conformal method. There is no asserted distribution-free coverage guarantee. Actual test coverage can fall below 90% and is shown in the results.

## Evaluation and limitations

Entire test profiles include unknown initial thermal states. The fixed benchmark uses 120 s faults starting at 45% of each profile. Bias is a +10 C coolant ramp; stuck values hold the pre-event reading. Silent errors receive no fault mask. Arbitrary dashboard settings can differ from this benchmark.

The ensemble/baseline comparison does not isolate fault training from ensembling, additional training data, or seed variation. There is no cross-motor validation, live CAN interface, automotive-controller timing study, physical-fault classifier, or closed-loop torque simulation. Advisories use illustrative thresholds and do not affect recorded temperatures.

## Browser inference

PyTorch trains the models. JSON contains exported weights and preprocessing constants. A browser worker executes real neural inference, rather than playing back stored predictions. A Node test compares the actual worker's features and predictions against Python on measured samples with a dropout. No external JavaScript libraries or CDN are required.

The worker feature function reads only the first seven operating columns. Target columns are used after inference for evaluation metrics and charts. Source labels remain present in the replay files because this is an evaluation demonstration.
