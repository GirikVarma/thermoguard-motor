# Five-minute demonstration and viva

## Before presenting

Extract the ZIP and open ThermoGuard_Standalone.html in a modern desktop browser. Alternatively run `python3 server.py`. Wait a few seconds for first inference. Keep the standalone file and ZIP on the presentation computer. Neither internet nor training is required.

## Demonstration

**0:00-0:45:** Explain that motor internal temperatures have thermal memory and are harder to measure than electrical signals. Show seven operating inputs and four estimated component temperatures. Measured internal temperatures are evaluation references, excluded from model inputs.

**0:45-2:00:** Use default held-out Profile 26 with a 120 s coolant dropout. Click Play or click within the highlighted event. Show availability flags, measured temperature, clean-trained baseline, robust ensemble, and upper estimate. Select Winding and Rotor magnet. Explain that the fault damages an input signal and leaves reference labels intact.

**2:00-3:00:** Select Two-channel dropout and Run experiment. Try a longer event. Then demonstrate Silent sensor drift and explain that no hidden fault flag is supplied to the model. Do not claim universal silent-fault detection.

**3:00-4:00:** Open Measured benchmarks. Explain the 34/7/13/15 whole-profile split and quote MAE in degrees Celsius. Upper coverage is empirical and can fall below its calibration target. The ensemble has three networks; the baseline has one, so this is not a controlled fault-training ablation.

**4:00-5:00:** Open How it works. Explain thermal-history filters and two hidden neural layers. Export a JSON experiment or CSV predictions. Explain that torque advice does not alter recorded temperatures or control hardware.

## Likely questions

**Is it deep learning?** Yes: each trained network has two learned hidden layers. Three fault-trained models form the displayed ensemble. Causal first-order filters provide temporal memory.

**Where is the physics?** Current-squared and power proxies reflect heating, and first-order history filters reflect thermal memory. The prototype does not enforce the complete thermal-network equations proposed for later work.

**Is the data real?** Operating inputs and temperature references are measured Paderborn motor recordings. Sensor faults are controlled injected perturbations.

**How is leakage prevented?** Profile IDs are disjoint. Only training data sets normalization and fallback values. Internal targets and torque are excluded from features. Processing uses no future samples.

**Does it work without sensors?** It handles selected missing operating inputs using the remaining signals, history, and missingness information. It does not infer temperature without operating information.

**Can it prevent overheating?** This version demonstrates estimation and advisory replay. That claim requires a separate closed-loop plant or hardware experiment.

**What remains for research?** Controlled single-model ablations, additional splits and motors, stronger uncertainty validation, realistic physical faults, embedded testing, and an exhaustive novelty review.
