# References and evidence status

**Checked on 24 October 2026.** These sources support dataset provenance and existing methods. The proposed robustness design, schedule, and success criteria are project choices requiring experiments.

## R1. Primary dataset

Wilhelm Kirchgassner, Oliver Wallscheid, and Joachim Bocker. *Electric Motor Temperature*, dataset version 2161054, 2021. DOI: 10.34740/KAGGLE/DSV/2161054.

https://www.kaggle.com/dsv/2161054

The public card describes approximately 185 hours of 2 Hz PMSM test-bench measurements and profile identifiers. The data archive, exact schema, and license must still be audited at acquisition. A public dataset page does not by itself authorize unrestricted redistribution.

## R2. Deep motor-temperature baseline

W. Kirchgassner, O. Wallscheid, and J. Bocker. *Estimating Electric Motor Temperatures With Deep Residual Machine Learning*. IEEE Transactions on Power Electronics, 36(7), 7480-7488, 2021. DOI: 10.1109/TPEL.2020.3045596.

https://doi.org/10.1109/TPEL.2020.3045596

Authors' implementation: https://github.com/upb-lea/deep-pmsm

The authors' repository identifies the journal issue year as 2021. The DOI contains 2020, reflecting the earlier publication history. This proposal follows the authors' issue citation.

## R3. Thermal neural network foundation

W. Kirchgassner, O. Wallscheid, and J. Bocker. *Thermal neural networks: Lumped-parameter thermal modeling with state-space machine learning*. Engineering Applications of Artificial Intelligence, 117, 105537, 2023. DOI: 10.1016/j.engappai.2022.105537.

https://doi.org/10.1016/j.engappai.2022.105537

Authors' implementation: https://github.com/wkirgsn/thermal-nn

Preprint: https://arxiv.org/abs/2103.16323

This establishes the heat-transfer-based neural modeling foundation. The project must cite it and document any implementation reuse and license requirements.

## R4. Recent hybrid-model prior art

*OLTEM: Lumped Thermal and Deep Neural Model for PMSM Temperature*. AI, 6(8), 173, 2025. DOI: 10.3390/ai6080173.

https://www.mdpi.com/2673-2688/6/8/173

This is a nearby hybrid-model study, so combining a thermal model with a neural network is not sufficient as a novelty claim. Verify full bibliographic metadata when building the final manuscript bibliography.

## R5. Recent sparse-sampling prior art

*A Physics-Informed Neural Network for PMSM Temperature Estimation Under Sparse Sampling Conditions*. Energies, 19(15), 3701, 2026. DOI: 10.3390/en19153701.

https://www.mdpi.com/1996-1073/19/15/3701

The title and publisher record establish nearby 2026 work. Sparse sampling and loss of an entire input channel are different experimental problems. Read the complete method before deciding which claims or comparisons the final paper requires.
