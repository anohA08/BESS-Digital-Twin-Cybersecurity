# Box 1 EKF diagnostic add-on

Run from repository root: `python -m unittest discover -s tests -v` and `python run_box1_ekf.py --profile all`.

This add-on does not modify the original ECM/EKF algorithms. It reports **pre-update** one-step voltage predictions rather than the artificially flattering post-update voltage fit. It uses the measured voltage only in the EKF measurement update, and uses the recorded SOC exclusively for evaluation. The input trajectories and lookup tables come from the old repository, so comparisons are **within-dataset exploratory**, not independent model validation.

The legacy EKF uses fixed process/measurement covariance settings and a simplified covariance update. No covariance or noise calibration is asserted. The report compares open-loop prediction with voltage-informed EKF prior prediction; differences do not independently establish SOC accuracy.
