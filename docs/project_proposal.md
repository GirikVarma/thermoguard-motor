# An EV motor that estimates its internal heat when sensors fail

**Detailed project proposal | 24 October 2026**

**Academic title:** Fault-Tolerant Thermal State Estimation for Electric Vehicle Traction Motors Using Physics-Guided Deep Learning.

**Working name:** ThermoGuard Motor. **Domain:** electrical drives, motor thermal modeling, deep learning. **Initial platform:** a permanent-magnet synchronous motor (PMSM) test-bench dataset.

## Project in one paragraph

The proposed system will estimate internal motor temperatures from electrical operating signals and accessible boundary temperatures. Its main purpose is to maintain useful temperature estimates when an input sensor stops reporting. A compact neural thermal model will combine a heat-transfer structure with learned nonlinear relationships. The project will compare ordinary training with training that deliberately masks sensor measurements, then assess conservative temperature bounds on entirely unseen measurement sessions. A dashboard will replay operating profiles and display the estimated rotor-magnet and stator temperatures, sensor availability, and an advisory torque limit. Recorded measurements will provide evaluation references. A separate optional simulator will assess the consequences of changing torque. The project will produce reproducible experiments and an evidence-based paper, including negative findings if the proposed method does not improve the baselines.

## Central research question

Can training a physics-guided thermal estimator to handle missing inputs reduce dangerous temperature underestimation during sensor dropouts on unseen motor operating profiles, while preserving useful accuracy during normal operation?

## Proposed outputs

- A documented data pipeline with splits by complete measurement session.
- Conventional, recurrent-neural, and thermal-neural reference models.
- Reproducible sensor-dropout experiments and an uncertainty evaluation.
- A replay dashboard with measured references available only for evaluation.
- A detailed paper and presentation supported by the measured results.

## Scope of this document

This is a proposal and implementation plan. The dataset archive has not yet been downloaded or audited locally. No model has been trained and no accuracy, protection benefit, or deployment performance has been measured. The literature establishes that neural motor-temperature estimation already exists; the proposed investigation concerns reliability during missing measurements [R1-R5].

<!-- pagebreak -->

# 1. Electrical engineering basis and scope

## Why the problem matters

Internal temperatures reflect accumulated losses and cooling history. A motor can remain hot after its instantaneous electrical load falls. Estimating temperatures therefore requires a dynamic state, rather than a regression using only the latest current and speed. The physical motivation is established in the motor thermal-modeling literature [R2, R3].

The project will estimate four instrumented evaluation targets: rotor permanent magnet (`pm`), stator winding, stator tooth, and stator yoke. These are component-level estimates, not a spatially resolved finite-element temperature field.

## Physical model

For thermal node k, a lumped heat balance is:

`C_k dT_k/dt = P_loss,k + sum_j G_kj (T_j - T_k)`

Here C is thermal capacitance, G is thermal conductance, and P_loss is generated heat. The proposed model will constrain capacitances and conductances to be positive and loss estimates to be nonnegative. These constraints improve physical plausibility but do not establish accurate material parameters or certified protection.

Useful electrical features include `i_d^2 + i_q^2`, `u_d*i_d + u_q*i_q`, and speed magnitude. The second quantity is an electrical-power proxy whose scaling depends on the d-q transformation convention. It must not be reported as measured motor efficiency. Regeneration still generates losses, so negative electrical power must not become negative heat generation.

## Primary operating inputs

| Signal group | Inputs | Reason for inclusion |
| --- | --- | --- |
| Electrical | i_d, i_q, u_d, u_q | Load and electrical-excitation information |
| Mechanical | motor_speed | Operating point and speed-dependent behavior |
| Cooling boundary | coolant | Accessible boundary-temperature measurement |
| Environment | ambient | Ambient-temperature boundary condition |

Measured shaft torque will be excluded from the primary estimator because it may require an instrument absent from a production drive. It may support descriptive analysis and an explicitly labeled upper-bound experiment. The four internal target temperatures will never be ordinary model inputs.

## Scope boundary

The core project covers one measured motor platform, missing-data robustness, and temperature estimation. Cross-vehicle transfer, mechanical fault classification, winding hotspot reconstruction, certified protection, and full-vehicle range improvement are outside the initial scope. The 2 Hz data will support thermal-timescale analysis, not switching-frequency fault detection [R1].

<!-- pagebreak -->

# 2. Research contribution and data protocol

## What is established and what will be investigated

| Established foundation | Proposed investigation |
| --- | --- |
| Deep recurrent and convolutional motor-temperature estimators [R2] | Behavior when an operating-input sensor becomes unavailable |
| Thermal neural networks with a heat-transfer structure [R3] | Effect of explicit missing-input masks and measurement-age features |
| Hybrid thermal/deep models and sparse-sampling studies [R4, R5] | Underestimation, uncertainty, and clean-versus-fault performance under one consistent protocol |

The project does not claim to invent thermal neural networks. Its candidate contribution is a reproducible reliability study and, if supported by experiments, an improved strategy for handling missing inputs. A focused review must check this exact combination before the final paper claims novelty.

## Dataset and provenance

The primary source is the Paderborn Electric Motor Temperature dataset. Its public card describes approximately 185 hours of test-bench recordings at 2 Hz, separated by `profile_id` [R1]. At acquisition, record the downloaded version, column schema, units, checksum, license, and source URL. Do not redistribute the archive until its actual license terms have been verified.

The source contains measured target temperatures for evaluating a virtual sensor. Artificial sensor faults will be introduced into copies of the input channels. Those faults are controlled experimental perturbations, not evidence that the original motor suffered physical faults.

## Separation before preprocessing

Use approximately 50% of whole profiles for training, 10% for validation, 20% for calibration, and 20% for final testing. Round by available profile count and publish the exact IDs in a manifest. Calibration should contain at least nine independent profiles for the proposed finite one-sided 90% profile-level bound. If too few profiles remain, revise the split or report empirical intervals instead.

Fit normalization, imputation constants, and feature transformations on training profiles only. Select architecture and early stopping using validation profiles. Use calibration profiles only to set the uncertainty correction. Open the test set after the experiment settings are frozen.

## Causal processing and initial conditions

Preserve row order within each profile. Do not create a time window that crosses a profile boundary, interpolate using future samples, or split overlapping windows across datasets. Reset model state at every new profile.

Initial internal temperatures are not observable from a single input sample. Start from an explicitly declared boundary-based estimate and report initial-transient errors separately, as well as full-profile errors. A study using measured initial target temperatures may appear only as an instrumented upper bound. Retaining a previous estimate is valid only within the same continuous session. Report a first-five-minute sensitivity analysis; this duration is a proposed diagnostic window, not a claim about physical settling time.

<!-- pagebreak -->

# 3. Model and sensor-failure design

<!-- architecture -->

## Reference models

**B0: simple dynamic regression.** Fit a regularized linear estimator using causal exponentially weighted electrical features. This establishes how much benefit comes from thermal history without a deep architecture.

**B1: compact GRU.** Use the same operating inputs and target temperatures, with no target-temperature feedback during deployment. It provides a conventional temporal deep-learning comparison.

**B2: thermal neural network.** Reproduce a compact version of the authors' public heat-transfer-based architecture and document all deviations [R3].

**Proposed B3: thermal neural network with missing-input training.** Add a validity mask and elapsed time since the last valid value for each input. Train on clean sequences mixed with declared dropout patterns. Compare B3 directly with B2 using the same backbone and optimization budget.

## Core failure protocol

| Scenario | Proposed perturbation | Interpretation |
| --- | --- | --- |
| F0: clean | Original operating signals | Accuracy cost of robustness |
| F1: coolant dropout | Remove one channel for 5, 30, or 120 s | Missing boundary-temperature measurement |
| F2: voltage dropout | Remove u_d or u_q for the same durations | Missing electrical telemetry |
| F3: combined dropout | Remove coolant and one voltage channel | Harder sensor combination |
| F4: unreported errors | Coolant bias ramp or stuck value | Stress test without an oracle fault flag |

The durations are proposed experimental settings, not dataset facts. Fault start times and seeds must be independent of target temperature. Keep unmodified reference channels and target values in evaluation-only storage.

## What the estimator knows

For F1-F3, use missing-sample flags that could come from the acquisition system. Fill inputs causally with a short last-valid-value hold, followed by a training-derived fallback; always expose the mask and age. Learn hold durations on validation data and freeze them before testing.

F4 is different: the sensor still reports a value, so do not provide the model with the injected onset or true fault mask. Measure degradation under bias and stuck-value stress. Automatic drift diagnosis is an extension requiring a separately evaluated detector. Naturally steady values must not automatically count as failed sensors.

## Training and numerical behavior

Use a temperature-regression loss, initially Huber, with a validation-selected penalty on positive underestimation `max(T_true - T_est, 0)`. Keep the penalty in a separate ablation to avoid attributing all gains to masking. Use a stable thermal integration step and check long-rollout behavior. Train all state transitions causally; do not substitute measured targets as hidden states during final evaluation.

<!-- pagebreak -->

# 4. Evaluation and uncertainty

## A fair comparison

Evaluate all models on identical complete test profiles and identical injected events. Train three random seeds per model when resources permit. Report variability across training seeds separately from uncertainty across test profiles. A final model selection must use validation data, never the best test result.

| Metric | Engineering interpretation |
| --- | --- |
| MAE and RMSE, in degrees Celsius | Average temperature-estimation error |
| 95th percentile positive underestimation | Tail of errors that hide overheating |
| Maximum positive underestimation | Worst observed miss, with its profile and time |
| Upper-bound coverage and width | Conservatism versus usefulness |
| Recovery after measurement return | Estimator behavior after a dropout |
| CPU inference time and model size | Feasibility on the tested computer |

Compute each metric per target and per profile. Report macro averages across profiles, pooled metrics, and the worst profile. Avoid reporting only R-squared or a percentage called temperature-prediction accuracy.

## Proposed conservative upper temperature bound

Train a small ensemble of three B3 models. Let `mu` be the ensemble mean and `sigma` its standard deviation. Use a small positive scale floor selected on validation data. For each calibration profile, calculate the maximum positive standardized error over all targets, all times, and a fixed suite of clean/dropout replays:

`s_g = max(0, max_(t,k,scenario) ((T_true - mu) / max(sigma, floor)))`

For alpha = 0.10, take the order statistic with index `ceil((n_cal + 1)*(1-alpha))`. If the required index exceeds the number of calibration profiles, a finite distribution-free bound is unavailable. Otherwise define `U = mu + q*max(sigma, floor)`.

This profile-level construction accommodates dependence within each profile by treating a complete profile as one calibration unit. Its nominal interpretation requires exchangeable calibration and test profiles under the same replay protocol. New motors, unreported drift, or a changed fault distribution invalidate that assumption. Report their empirical coverage separately. Ensemble disagreement alone is not a calibrated probability.

## Success criterion and reporting

The primary comparison is B3 versus B2 on the predeclared F1-F3 suite. The candidate target is at least a 15% reduction in macro-averaged 95th-percentile positive underestimation, with no more than a 10% increase in clean macro MAE. These are proposed engineering targets, not expected or achieved results. Also report the absolute errors and profile-bootstrap intervals; percentage gains near a zero baseline can mislead.

A useful negative result is acceptable: if missing-input training fails to improve the baseline, explain which signals or initial conditions make the state insufficiently observable. The research contribution then becomes a transparent benchmark and its limitations.

<!-- pagebreak -->

# 5. Demonstration, control extension, and research limits

## Dashboard specification

The initial application will replay measured profiles. Its main panel will display a schematic of the rotor magnet, winding, tooth, and yoke, colored by estimated component temperature. Call it a component-temperature schematic, not a measured spatial heatmap. A trace panel will show estimates and upper bounds, with ground truth available through an evaluation toggle. A sensor panel will show channel availability and time since the latest valid reading.

The operator will choose a held-out profile, inject a declared dropout, and compare the clean-trained and fault-trained estimators. A visible label will distinguish injected data faults from physical motor faults. Each replay will record its profile, seed, model checkpoint, and settings.

## Advisory torque limit

An optional display can translate each upper temperature bound into a torque multiplier:

`r_k = clip((L_k - U_k)/(L_k - W_k), 0, 1)`

`r = min_k r_k`

W and L are component-specific warning and stop settings, with W below L. Production values require motor specifications and engineering validation. Until those exist, any selected settings are illustrative and must appear as such. The dataset's torque channel is measured shaft torque, not a requested torque command.

## What recorded replay can demonstrate

Replay can show when an advisory would have reduced a hypothetical request. It cannot show that torque reduction actually cooled the motor, prevented a violation, or preserved vehicle performance, because the recorded temperatures do not respond to the new command.

For a control-effect study, implement a separate motor/thermal plant with a synthetic requested-torque profile. Perturb plant parameters independently of the estimator and evaluate thermal-limit exceedance, delivered mechanical work, and unnecessary derating. Report all results as simulation-dependent. Retain independent hard limits in any future hardware experiment.

## Limitations to carry into the final paper

- One motor platform does not demonstrate cross-motor or cross-manufacturer transfer.
- Injected signal faults do not reproduce all physical sensor or cooling failures.
- Sparse inputs cannot uniquely reveal every unknown initial thermal condition.
- Low average error can coexist with a dangerous isolated underestimation.
- Nominal uncertainty coverage does not establish coverage under arbitrary distribution shifts.
- A software timing measurement does not establish execution time on an automotive controller.

The paper will use the terms "virtual thermal sensor" and "thermal estimator." A live digital-twin or real-time deployment claim requires the corresponding integration and timing evidence.
