
"""Current-conditioned voltage residual evidence for BESS Box 2.

The production residual is abs(measured_voltage - predicted_voltage), in volts.
Only compare samples and calibrations with matching voltage scale, operating
condition, and prediction timing. Scores are ordinal anomaly evidence (0–2),
not attack probabilities.
"""

import json
import math
from numbers import Real
from pathlib import Path


class VoltageEvidence:
    """Voltage evidence with condition-calibrated and legacy threshold modes.

    Explicit p95_threshold and p99_threshold select legacy mode, bypassing
    configuration loading. Otherwise, thresholds are selected by condition.
    Condition labels must be sourced from a trusted experiment/controller
    setting, not a potentially compromised measured current.
    """

    VALID_CONDITIONS = frozenset(("1A", "1.5A", "2A"))
    EPSILON = 1e-6

    def __init__(
        self,
        p95_threshold=None,
        p99_threshold=None,
        default_condition="2A",
        condition_thresholds=None,
    ):
        self._validate_condition(default_condition)
        self.default_condition = default_condition

        if (p95_threshold is None) != (p99_threshold is None):
            raise ValueError(
                "p95_threshold and p99_threshold must both be supplied or omitted"
            )

        self._legacy_mode = p95_threshold is not None
        if self._legacy_mode:
            p95, p99 = self._validated_pair(
                p95_threshold, p99_threshold, "legacy"
            )
            self.p95_threshold = p95
            self.p99_threshold = p99
            self.condition_thresholds = {}
        else:
            self.p95_threshold = None
            self.p99_threshold = None
            raw_thresholds = (
                self._load_condition_thresholds()
                if condition_thresholds is None
                else condition_thresholds
            )
            if not isinstance(raw_thresholds, dict):
                raise TypeError("condition_thresholds must be a dictionary")
            missing = self.VALID_CONDITIONS - raw_thresholds.keys()
            if missing:
                raise ValueError(f"Missing voltage conditions: {sorted(missing)}")
            self.condition_thresholds = {}
            for condition in sorted(self.VALID_CONDITIONS):
                record = raw_thresholds[condition]
                if not isinstance(record, dict):
                    raise TypeError(f"{condition} thresholds must be a dictionary")
                if "p95" not in record or "p99" not in record:
                    raise ValueError(f"{condition} requires p95 and p99")
                p95, p99 = self._validated_pair(
                    record["p95"], record["p99"], condition
                )
                self.condition_thresholds[condition] = {
                    "p95": p95,
                    "p99": p99,
                }

    # ============================================================
    # NUMERICAL VALIDATION
    # ============================================================

    @staticmethod
    def _finite(name, value, minimum=None):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{name} must be a real number")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        if minimum is not None and value < minimum:
            raise ValueError(f"{name} must be >= {minimum}")
        return value

    @classmethod
    def _validated_pair(cls, p95, p99, label):
        p95 = cls._finite(f"{label}.p95", p95, minimum=0.0)
        p99 = cls._finite(f"{label}.p99", p99, minimum=0.0)
        if p99 < p95:
            raise ValueError(f"{label}.p99 must be >= p95")
        return p95, p99

    @classmethod
    def _validate_condition(cls, condition):
        if condition not in cls.VALID_CONDITIONS:
            raise ValueError("condition must be '1A', '1.5A', or '2A'")

    # ============================================================
    # CALIBRATION FILE
    # ============================================================

    @staticmethod
    def _load_condition_thresholds():
        path = (
            Path(__file__).resolve().parent
            / "config"
            / "box2_calibration.json"
        )
        if not path.is_file():
            raise FileNotFoundError(
                f"Box-2 calibration file not found: {path}"
            )

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        try:
            return data["normal_voltage_calibration"]["conditions"]
        except (KeyError, TypeError) as exc:
            raise ValueError(
                "Calibration JSON must contain "
                "normal_voltage_calibration.conditions"
            ) from exc

    # ============================================================
    # VOLTAGE RESIDUAL
    # ============================================================

    @classmethod
    def calculate_error(cls, measured_voltage, predicted_voltage):
        measured = cls._finite(
            "measured_voltage", measured_voltage
        )
        predicted = cls._finite(
            "predicted_voltage", predicted_voltage
        )
        return abs(measured - predicted)

    # ============================================================
    # THRESHOLD SELECTION
    # ============================================================

    def get_thresholds(self, condition=None):
        if condition is None:
            condition = self.default_condition

        self._validate_condition(condition)

        if self._legacy_mode:
            return {
                "p95": self.p95_threshold,
                "p99": self.p99_threshold,
            }

        # Return a copy to prevent accidental threshold modification.
        return self.condition_thresholds[condition].copy()

    # ============================================================
    # EVIDENCE SCORING
    # ============================================================

    def _score_error(self, error, thresholds):
        if error <= thresholds["p95"] + self.EPSILON:
            return 0

        if error <= thresholds["p99"] + self.EPSILON:
            return 1

        return 2

    def calculate_score(
        self,
        measured_voltage,
        predicted_voltage,
        condition=None,
    ):
        error = self.calculate_error(
            measured_voltage, predicted_voltage
        )
        thresholds = self.get_thresholds(condition)

        return self._score_error(error, thresholds)

    # ============================================================
    # COMPLETE EVALUATION
    # ============================================================

    def evaluate(
        self,
        measured_voltage,
        predicted_voltage,
        condition=None,
    ):
        selected_condition = (
            self.default_condition if condition is None else condition
        )

        thresholds = self.get_thresholds(selected_condition)
        error = self.calculate_error(
            measured_voltage, predicted_voltage
        )

        return {
            "voltage_error": error,
            "p95_threshold": thresholds["p95"],
            "p99_threshold": thresholds["p99"],
            "voltage_score": self._score_error(
                error, thresholds
            ),
            "condition": selected_condition,
        }
