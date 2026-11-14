
"""Temporal evidence for digital-twin BESS Box 2.

SOC is in percentage points (0-100); timestamps and expected_interval
must share a unit (e.g., minutes). This detector reports anomaly evidence,
not a confirmed cyberattack or calibrated attack probability.
"""

import math
from numbers import Integral, Real


class TemporalEvidence:
    """Stateful jump, repetition, and sampling-gap evidence.

    Baseline settings retain the original behavior. Optionally provide an
    independent expected_soc_change (percentage points per sample) from a
    physics predictor to suppress repetition alerts when a flat SOC is
    physically expected (idle or very low-current operation).

    Maintain one instance per sensor stream, in timestamp order. Call reset()
    when a new run/stream begins.
    """

    def __init__(
        self,
        jump_threshold=5.0,
        repeat_limit=3,
        delay_threshold=2.0,
        tolerance=0.001,
    ):
        self.jump_threshold = self._number(
            "jump_threshold", jump_threshold, minimum=0.0
        )

        if (
            isinstance(repeat_limit, bool)
            or not isinstance(repeat_limit, Integral)
            or repeat_limit < 1
        ):
            raise ValueError(
                "repeat_limit must be a positive integer"
            )

        self.repeat_limit = int(repeat_limit)

        self.delay_threshold = self._number(
            "delay_threshold", delay_threshold, minimum=0.0
        )

        self.tolerance = self._number(
            "tolerance", tolerance, minimum=0.0
        )

        self.reset()

    # ============================================================
    # NUMERICAL VALIDATION
    # ============================================================

    @staticmethod
    def _number(name, value, minimum=None, maximum=None):

        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(
                f"{name} must be a real number"
            )

        value = float(value)

        if not math.isfinite(value):
            raise ValueError(
                f"{name} must be finite"
            )

        if minimum is not None and value < minimum:
            raise ValueError(
                f"{name} must be >= {minimum}"
            )

        if maximum is not None and value > maximum:
            raise ValueError(
                f"{name} must be <= {maximum}"
            )

        return value

    # ============================================================
    # TEMPORAL EVALUATION
    # ============================================================

    def evaluate(
        self,
        measured_soc,
        timestamp,
        expected_interval=1.0,
        expected_soc_change=None,
    ):
        """
        Evaluate a new measurement.

        expected_soc_change:
            Optional independent prediction of signed SOC
            change in percentage points for the current
            sampling interval.

            Do not derive it from the suspicious SOC measurement.
        """

        soc = self._number(
            "measured_soc",
            measured_soc,
            minimum=0.0,
            maximum=100.0,
        )

        t = self._number(
            "timestamp",
            timestamp,
        )

        interval = self._number(
            "expected_interval",
            expected_interval,
            minimum=0.0,
        )

        if interval == 0.0:
            raise ValueError(
                "expected_interval must be > 0"
            )

        if expected_soc_change is not None:
            expected_soc_change = self._number(
                "expected_soc_change",
                expected_soc_change,
            )

        # Validate time before updating stored measurements.
        elapsed = None

        if self.previous_timestamp is not None:
            elapsed = t - self.previous_timestamp

            if elapsed < 0:
                raise ValueError(
                    "Timestamp cannot move backward."
                )

        soc_change = None
        jump_detected = False
        repeat_detected = False
        delay_detected = False
        idle_suppressed_repeat = False

        # --------------------------------------------------------
        # SOC temporal consistency
        # --------------------------------------------------------

        if self.previous_soc is not None:

            soc_change = abs(
                soc - self.previous_soc
            )

            jump_detected = (
                soc_change > self.jump_threshold
            )

            repeated = (
                soc_change <= self.tolerance
            )

            # Physical predictor indicates little SOC change.
            idle_expected = (
                expected_soc_change is not None
                and abs(expected_soc_change) <= self.tolerance
            )

            idle_suppressed_repeat = bool(
                repeated and idle_expected
            )

            if repeated and not idle_expected:
                self.repeat_count += 1
            else:
                self.repeat_count = 0

            repeat_detected = (
                self.repeat_count >= self.repeat_limit
            )

        # --------------------------------------------------------
        # Timestamp delay detection
        # --------------------------------------------------------

        if elapsed is not None:

            delay_detected = (
                elapsed > interval + self.delay_threshold
            )

        # --------------------------------------------------------
        # Evidence severity
        # --------------------------------------------------------

        violations = (
            int(jump_detected)
            + int(repeat_detected)
            + int(delay_detected)
        )

        score = min(violations, 2)

        # --------------------------------------------------------
        # Update temporal memory
        # --------------------------------------------------------

        self.previous_soc = soc
        self.previous_timestamp = t

        # --------------------------------------------------------
        # Results
        # --------------------------------------------------------

        return {
            "temporal_score": score,
            "jump_detected": jump_detected,
            "repeat_detected": repeat_detected,
            "delay_detected": delay_detected,
            "repeat_count": self.repeat_count,

            # Additional diagnostic outputs
            "soc_change": soc_change,
            "elapsed_interval": elapsed,
            "idle_suppressed_repeat": idle_suppressed_repeat,
        }

    # ============================================================
    # RESET
    # ============================================================

    def reset(self):

        self.previous_soc = None
        self.repeat_count = 0
        self.previous_timestamp = None
