
"""Box 2 measurement freshness evidence.

Measurement age = receive_timestamp - source_timestamp.

Both timestamps must use the same clock and time unit.

P95/P99 defaults (0, 1) are legacy baselines, not generally
validated calibration values.

This detector cannot identify replay whose timestamps have
been rewritten.
"""

import math
from numbers import Real


class FreshnessEvidence:
    """
    Score timestamp age on the existing 0/1/2 Box 2 evidence scale.

    All units are those of the timestamps (minutes in the
    existing delay experiments).

    Assumes source and receiver clocks are synchronized.

    For real unsynchronized clocks, calibrate clock offset
    and jitter first.
    """

    EPSILON = 1e-6

    def __init__(
        self,
        p95_threshold=0.0,
        p99_threshold=1.0,
    ):
        self.p95_threshold = self._finite_nonnegative(
            "p95_threshold",
            p95_threshold,
        )

        self.p99_threshold = self._finite_nonnegative(
            "p99_threshold",
            p99_threshold,
        )

        if self.p99_threshold < self.p95_threshold:
            raise ValueError(
                "p99_threshold must be >= p95_threshold"
            )

    # ============================================================
    # INPUT VALIDATION
    # ============================================================

    @staticmethod
    def _finite_number(name, value):

        if isinstance(value, bool) or not isinstance(
            value, Real
        ):
            raise TypeError(
                f"{name} must be a real number"
            )

        result = float(value)

        if not math.isfinite(result):
            raise ValueError(
                f"{name} must be finite"
            )

        return result

    @classmethod
    def _finite_nonnegative(cls, name, value):

        result = cls._finite_number(name, value)

        if result < 0.0:
            raise ValueError(
                f"{name} cannot be negative"
            )

        return result

    # ============================================================
    # MEASUREMENT AGE
    # ============================================================

    def calculate_age(
        self,
        receive_timestamp,
        source_timestamp,
    ):
        """
        Return nonnegative measurement age.

        The result uses the same unit as the timestamps.
        """

        received = self._finite_number(
            "receive_timestamp",
            receive_timestamp,
        )

        source = self._finite_number(
            "source_timestamp",
            source_timestamp,
        )

        age = received - source

        if not math.isfinite(age):
            raise ValueError(
                "Calculated measurement age must be finite"
            )

        if age < 0.0:
            raise ValueError(
                "source_timestamp cannot be later than "
                "receive_timestamp; check time synchronization"
            )

        return age

    # ============================================================
    # EVIDENCE SCORING
    # ============================================================

    def _score_age(self, age):
        """
        Translate validated age into ordinal evidence.
        """

        if age <= self.p95_threshold + self.EPSILON:
            return 0

        if age <= self.p99_threshold + self.EPSILON:
            return 1

        return 2

    def calculate_score(
        self,
        receive_timestamp,
        source_timestamp,
    ):
        """
        Calculate freshness evidence severity.
        """

        age = self.calculate_age(
            receive_timestamp,
            source_timestamp,
        )

        return self._score_age(age)

    # ============================================================
    # COMPLETE FRESHNESS EVALUATION
    # ============================================================

    def evaluate(
        self,
        receive_timestamp,
        source_timestamp,
    ):
        """
        Return original Box 2 output fields.
        """

        age = self.calculate_age(
            receive_timestamp,
            source_timestamp,
        )

        return {
            "measurement_age": age,
            "p95_threshold": self.p95_threshold,
            "p99_threshold": self.p99_threshold,
            "freshness_score": self._score_age(age),
        }
