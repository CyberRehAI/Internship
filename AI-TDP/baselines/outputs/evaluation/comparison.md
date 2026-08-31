# Baseline comparison

Coarse labels: Val = normal, Test = attack-period. Threshold = Val score quantile. ROC/PR on Val∪Test.

| model_id | quantile | threshold | Val FPR | Test detection | F1 (V∪T) | ROC-AUC | PR-AUC |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| lstm_ae_net | 0.95 | 243.884 | 0.0507 | 0.0562 | 0.1052 | 0.5506 | 0.8128 |
| stacked_cascade | 0.95 | 100.051 | 0.0625 | 1.0000 | 0.9697 | 1.0000 | 1.0000 |
| tranad_concat | 0.95 | 10.1094 | 0.0507 | 0.9827 | 0.9850 | 0.9912 | 0.9981 |
| usad_concat | 0.95 | 10.3186 | 0.0507 | 0.9820 | 0.9847 | 0.9909 | 0.9980 |
