import math
from numbers import Integral, Real


class PersistenceAssessment:
    """Classify fusion evidence using persistence.

    Consecutive mode (default):
      - score > candidate_min increments a consecutive counter
      - otherwise the counter resets to zero
      - ABNORMAL after persistence_limit consecutive candidate samples

    Optional leaky mode:
      - candidate samples add 1 to a floating evidence accumulator
      - other samples decay the accumulator by decay_factor
      - ABNORMAL requires both current candidate evidence and an accumulator
        reaching persistence_limit; this prevents alerting purely on memory

    Scores > normal_score_max but not confirmed abnormal are SUSPICIOUS.
    """

    NORMAL_SCORE_MAX = 1.0
    ABNORMAL_CANDIDATE_MIN = 3.0

    def __init__(
        self,
        persistence_limit: int = 3,
        *,
        normal_score_max: float = 1.0,
        abnormal_candidate_min: float = 3.0,
        mode: str = "consecutive",
        decay_factor: float = 0.5,
    ):
        self.normal_score_max = self._finite_number(
            "normal_score_max", normal_score_max, minimum=0.0
        )
        self.abnormal_candidate_min = self._finite_number(
            "abnormal_candidate_min", abnormal_candidate_min, minimum=0.0
        )

        if (
            isinstance(persistence_limit, bool)
            or not isinstance(persistence_limit, Integral)
            or persistence_limit < 1
        ):
            raise ValueError("persistence_limit must be at least 1")

        if self.normal_score_max >= self.abnormal_candidate_min:
            raise ValueError(
                "normal_score_max must be less than abnormal_candidate_min"
            )

        if mode not in ("consecutive", "leaky"):
            raise ValueError("mode must be 'consecutive' or 'leaky'")

        self.decay_factor = self._finite_number(
            "decay_factor", decay_factor, minimum=0.0
        )

        if self.decay_factor >= 1.0:
            raise ValueError("decay_factor must be less than 1")

        self.persistence_limit = int(persistence_limit)
        self.mode = mode
        self.reset()

    # ============================================================
    # INPUT VALIDATION
    # ============================================================

    @staticmethod
    def _finite_number(name, value, minimum=None):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(
                f"{name} must be a finite real number"
            )

        value = float(value)

        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")

        if minimum is not None and value < minimum:
            raise ValueError(f"{name} must be >= {minimum}")

        return value

    # ============================================================
    # PERSISTENCE UPDATE
    # ============================================================

    def update(self, fusion_score: float) -> dict:
        """Consume one fused score and update the persistence state."""

        score = self._finite_number(
            "fusion_score", fusion_score, minimum=0.0
        )

        candidate = score > self.abnormal_candidate_min

        # Original consecutive candidate counter.
        if candidate:
            self.abnormal_count += 1
        else:
            self.abnormal_count = 0

        if self.mode == "consecutive":
            # Exact original persistence behavior.
            self.evidence_accumulator = float(
                self.abnormal_count
            )

            triggered = (
                self.abnormal_count >= self.persistence_limit
            )

        else:
            # Optional leaky accumulation.
            if candidate:
                self.evidence_accumulator += 1.0
            else:
                self.evidence_accumulator *= self.decay_factor

            triggered = (
                candidate
                and self.evidence_accumulator
                >= self.persistence_limit
            )

        # --------------------------------------------------------
        # Final classification
        # --------------------------------------------------------

        if triggered:
            classification = "ABNORMAL"

        elif score > self.normal_score_max:
            classification = "SUSPICIOUS"

        else:
            classification = "NORMAL"

        return {
            "abnormal_count": self.abnormal_count,
            "persistence_limit": self.persistence_limit,
            "raw_fusion_score": score,
            "final_classification": classification,

            # Additional research diagnostics.
            "persistence_mode": self.mode,
            "evidence_accumulator": self.evidence_accumulator,
            "abnormal_candidate": candidate,
        }

    # ============================================================
    # RESET
    # ============================================================

    def reset(self) -> None:
        """Clear evidence memory between independent simulation runs."""
        self.abnormal_count = 0
        self.evidence_accumulator = 0.0

    # ============================================================
    # ACCESSOR
    # ============================================================

    def get_abnormal_count(self) -> int:
        """Return consecutive candidate count, including in leaky mode."""
        return self.abnormal_count