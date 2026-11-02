# Model selection

Linear SVM was selected by the highest validation macro F1 (0.9929 versus 0.9582). Final test results
also favor it: macro F1 0.9800 versus 0.9608, 0.679 versus 0.830 ms/article in this run, and 0.93 MiB
versus 3.80 MiB serialized. It is therefore the stronger Railway baseline. Its decision-function
scores remain uncalibrated margins and are not exposed as probabilities.

