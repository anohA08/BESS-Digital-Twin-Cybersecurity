"""Interpretable attack-signature classifier for BESS Box 2.

This class recognizes heuristic evidence patterns; it does not certify that an
attack occurred. The independent persistence / situation-assessment stage
makes the operational decision. 'confidence' denotes rule strength only,
not a calibrated probability of attack or of safe operation.
"""
import math
from numbers import Real


class AttackTypeClassifier:
    """Classify one timestep using five ordinal evidence channels (0, 1, 2).

    Output keys and the classify() signature are backward-compatible.
    The fused score is validated, but is NOT used as an independent feature:
    it is derived from the evidence inputs and would double-count them.
    """

    @staticmethod
    def _score(name, value):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{name} must be numeric")
        value = float(value)
        if not math.isfinite(value) or not 0 <= value <= 2:
            raise ValueError(f"{name} must be finite and within [0, 2]")
        return value

    @staticmethod
    def _result(attack_type, confidence, reason):
        return {
            "attack_type": attack_type,
            "confidence": confidence,
            "reason": reason,
        }

    def classify(
        self,
        sync_score,
        physics_score,
        temporal_score,
        voltage_score,
        freshness_score,
        fusion_score,
    ):
        s = self._score("sync_score", sync_score)
        p = self._score("physics_score", physics_score)
        t = self._score("temporal_score", temporal_score)
        v = self._score("voltage_score", voltage_score)
        f = self._score("freshness_score", freshness_score)

        if isinstance(fusion_score, bool) or not isinstance(
            fusion_score, Real
        ):
            raise TypeError("fusion_score must be numeric")

        if (
            not math.isfinite(float(fusion_score))
            or fusion_score < 0
        ):
            raise ValueError(
                "fusion_score must be finite and nonnegative"
            )

        # Strong measurement age evidence indicates lateness.
        # If synchronization and temporal patterns overlap,
        # replay is plausible, but ordinary delay remains possible.
        if f >= 2:
            if s >= 1 and t >= 1:
                return self._result(
                    "REPLAY",
                    "MEDIUM",
                    "Stale data plus synchronization/temporal "
                    "inconsistency; replay is plausible, but "
                    "network delay is an alternative.",
                )

            return self._result(
                "COMMUNICATION_DELAY",
                "HIGH",
                "Strong measurement-age violation; delayed "
                "delivery is indicated, not necessarily a cyberattack.",
            )

        # Strong physics, synchronization and temporal evidence
        # can be compatible with more than one attack mechanism.
        if p >= 2 and s >= 1 and t >= 1 and f == 0:
            return self._result(
                "SENSOR_SPOOFING",
                "MEDIUM",
                "Strong physics and synchronization evidence; "
                "spoofing is prioritized under the baseline rules, "
                "although replay cannot be excluded.",
            )

        # Spoofing-like pattern without temporal inconsistency.
        if p >= 2 and s >= 1 and t == 0:
            return self._result(
                "SENSOR_SPOOFING",
                "MEDIUM",
                "Strong physics and synchronization disagreement "
                "without a temporal signature; sensor manipulation "
                "is plausible.",
            )

        # A corroborated replay-like evidence pattern.
        if (
            t >= 1
            and s >= 1
            and (p >= 1 or f >= 1)
        ):
            return self._result(
                "REPLAY",
                "MEDIUM",
                "Synchronization and temporal evidence with "
                "corroboration; could also reflect benign delay "
                "or changing operation.",
            )

        # Moderate communication-related evidence.
        if f >= 1 and t >= 1:
            return self._result(
                "COMMUNICATION_DELAY",
                "MEDIUM",
                "Measurement age and temporal gap jointly "
                "suggest delayed data.",
            )

        # Unresolved physics anomaly: more evidence needed.
        if (
            p >= 2
            and s == 0
            and t == 0
            and f == 0
            and v >= 1
        ):
            return self._result(
                "AMBIGUOUS_SPOOFING_OR_ROLLING_REPLAY",
                "LOW",
                "Physics anomaly without sufficient distinguishing "
                "signatures; model mismatch or operational changes "
                "remain possible.",
            )

        # No supported attack-specific signature.
        return self._result(
            "NORMAL",
            "LOW",
            "No modeled attack-specific signature matched; "
            "this does not establish measurement integrity "
            "or operational safety.",
        )