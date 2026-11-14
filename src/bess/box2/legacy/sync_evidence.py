
"""Synchronization evidence for Box 2 of a BESS digital-twin study.

Primary residual: abs(twin_soc - measured_soc), in percentage points.
EKF SOC is diagnostic only.

IMPORTANT: Existing box2-sync-v1 thresholds were calibrated by measured SOC.
The safer twin-based region selector requires separately recalibrated envelopes.
"""

import json
import math
from pathlib import Path


class SynchronizationEvidence:
    """Score a synchronization residual against SOC-region normal envelopes.

    Parameters
    ----------
    envelopes : mapping or None
        Three SOC regions (high/middle/low), each with p95 and p99.
        If None, load config/box2_calibration.json relative to this file.
    region_source : {'measured', 'twin'}
        'measured' reproduces the existing calibration methodology.
        'twin' prevents an attacked measured SOC from choosing its own region;
        use ONLY with envelopes recalibrated using twin SOC as selector.
    """

    VALID_REGIONS = ("high", "middle", "low")
    VALID_REGION_SOURCES = ("measured", "twin")
    EPSILON = 1e-6

    def __init__(self, envelopes=None, region_source="measured"):
        if region_source not in self.VALID_REGION_SOURCES:
            raise ValueError("region_source must be 'measured' or 'twin'")
        self.region_source = region_source
        self.envelopes = (
            self._load_calibrated_envelopes()
            if envelopes is None else envelopes
        )
        self._validate_envelopes()

    @staticmethod
    def _load_calibrated_envelopes():
        config_path = Path(__file__).resolve().parent / "config" / "box2_calibration.json"
        if not config_path.is_file():
            raise FileNotFoundError(f"Box-2 calibration file not found: {config_path}")
        with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)
        try:
            return config["normal_sync_calibration"]["envelopes"]
        except (KeyError, TypeError) as exc:
            raise ValueError(
                "Calibration JSON must contain normal_sync_calibration.envelopes"
            ) from exc

    @staticmethod
    def _finite_number(name, value, *, lower=None, upper=None):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a numeric value")
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        if lower is not None and value < lower:
            raise ValueError(f"{name} must be >= {lower}")
        if upper is not None and value > upper:
            raise ValueError(f"{name} must be <= {upper}")
        return float(value)

    def _validate_envelopes(self):
        if not isinstance(self.envelopes, dict):
            raise TypeError("envelopes must be a mapping")
        if set(self.envelopes) != set(self.VALID_REGIONS):
            raise ValueError("envelopes must contain exactly: high, middle, low")
        for region in self.VALID_REGIONS:
            thresholds = self.envelopes[region]
            if not isinstance(thresholds, dict):
                raise TypeError(f"{region} thresholds must be a mapping with p95 and p99")
            if "p95" not in thresholds or "p99" not in thresholds:
                raise ValueError(f"{region} requires both p95 and p99")
            p95 = self._finite_number(f"{region}.p95", thresholds["p95"], lower=0)
            p99 = self._finite_number(f"{region}.p99", thresholds["p99"], lower=0)
            if p99 < p95:
                raise ValueError(f"{region}.p99 must be >= {region}.p95")

    def get_soc_region(self, soc):
        soc = self._finite_number("soc", soc, lower=0, upper=100)
        return "high" if soc >= 80 else "middle" if soc >= 40 else "low"

    def get_thresholds(self, soc):
        return self.envelopes[self.get_soc_region(soc)].copy()

    def calculate_error(self, ekf_soc, twin_soc, measured_soc):
        # Validate EKF even though it is not part of the production residual.
        self._finite_number("ekf_soc", ekf_soc, lower=0, upper=100)
        twin = self._finite_number("twin_soc", twin_soc, lower=0, upper=100)
        measured = self._finite_number("measured_soc", measured_soc, lower=0, upper=100)
        return abs(twin - measured)

    def _selected_soc(self, twin_soc, measured_soc):
        return twin_soc if self.region_source == "twin" else measured_soc

    def calculate_score(self, ekf_soc, twin_soc, measured_soc):
        error = self.calculate_error(ekf_soc, twin_soc, measured_soc)
        thresholds = self.get_thresholds(self._selected_soc(twin_soc, measured_soc))
        if error <= thresholds["p95"] + self.EPSILON:
            return 0
        if error <= thresholds["p99"] + self.EPSILON:
            return 1
        return 2

    def evaluate(self, ekf_soc, twin_soc, measured_soc):
        error = self.calculate_error(ekf_soc, twin_soc, measured_soc)
        selected_soc = self._selected_soc(twin_soc, measured_soc)
        region = self.get_soc_region(selected_soc)
        thresholds = self.get_thresholds(selected_soc)
        if error <= thresholds["p95"] + self.EPSILON:
            score = 0
        elif error <= thresholds["p99"] + self.EPSILON:
            score = 1
        else:
            score = 2
        return {
            "sync_error": error,
            "soc_region": region,
            "normal_p95": thresholds["p95"],
            "normal_p99": thresholds["p99"],
            "sync_score": score,
            "ekf_twin_error": abs(ekf_soc - twin_soc),
            "sensor_soc": measured_soc,
            "twin_soc": twin_soc,
            "ekf_soc": ekf_soc,
        }
