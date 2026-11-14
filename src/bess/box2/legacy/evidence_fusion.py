
"""Validated, backward-compatible evidence fusion for BESS Box 2.

Scores from each detector must be between 0 (normal) and 2
(strongly suspicious). Fusion thresholds are initial baselines and
must be calibrated on suitable experimental datasets.
"""

import math


class EvidenceFusion:
    """
    Weighted fusion of five evidence channels:
        1. Synchronization
        2. Physics
        3. Temporal
        4. Voltage / model
        5. Freshness

    The first four arguments of calculate_score() and fuse()
    preserve the existing four-channel API.

    Freshness is optional and defaults to zero.

    IMPORTANT:
    The confidence field is retained for compatibility.
    It represents fused evidence severity, NOT a calibrated
    probability of attack or confidence in system safety.
    """

    def __init__(
        self,
        sync_weight=1.0,
        physics_weight=1.0,
        temporal_weight=1.0,
        voltage_weight=1.0,
        freshness_weight=1.0,
        normal_max=1.0,
        suspicious_max=3.0,
    ):
        weights = {
            "sync_weight": sync_weight,
            "physics_weight": physics_weight,
            "temporal_weight": temporal_weight,
            "voltage_weight": voltage_weight,
            "freshness_weight": freshness_weight,
        }

        for name, weight in weights.items():
            self._validate_number(
                name, weight, minimum=0.0
            )

        self._validate_number(
            "normal_max", normal_max, minimum=0.0
        )
        self._validate_number(
            "suspicious_max", suspicious_max, minimum=0.0
        )

        if normal_max >= suspicious_max:
            raise ValueError(
                "normal_max must be strictly below suspicious_max"
            )

        self.sync_weight = float(sync_weight)
        self.physics_weight = float(physics_weight)
        self.temporal_weight = float(temporal_weight)
        self.voltage_weight = float(voltage_weight)
        self.freshness_weight = float(freshness_weight)

        self.normal_max = float(normal_max)
        self.suspicious_max = float(suspicious_max)

    # ============================================================
    # INPUT VALIDATION
    # ============================================================

    @staticmethod
    def _validate_number(
        name, value, minimum=None, maximum=None
    ):
        if isinstance(value, bool) or not isinstance(
            value, (int, float)
        ):
            raise TypeError(
                f"{name} must be a finite numeric value"
            )

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

    @classmethod
    def _validate_evidence(cls, name, score):
        cls._validate_number(
            name,
            score,
            minimum=0.0,
            maximum=2.0,
        )

        # Continuous evidence values in [0, 2] are supported.

    # ============================================================
    # FUSION SCORE
    # ============================================================

    def calculate_score(
        self,
        sync_score,
        physics_score,
        temporal_score,
        voltage_score,
        freshness_score=0,
    ):
        """
        Calculate the weighted evidence score.

        An unnormalized weighted sum is used to preserve
        compatibility with the original Box 2 scoring scale.
        """

        evidence = {
            "sync_score": sync_score,
            "physics_score": physics_score,
            "temporal_score": temporal_score,
            "voltage_score": voltage_score,
            "freshness_score": freshness_score,
        }

        for name, value in evidence.items():
            self._validate_evidence(name, value)

        score = (
            self.sync_weight * sync_score
            + self.physics_weight * physics_score
            + self.temporal_weight * temporal_score
            + self.voltage_weight * voltage_score
            + self.freshness_weight * freshness_score
        )

        return float(score)

    # ============================================================
    # CLASSIFICATION
    # ============================================================

    def classify(self, score):
        """
        Assign evidence severity using configurable thresholds.

        Default:
            score <= 1 : NORMAL
            score <= 3 : SUSPICIOUS
            score > 3  : ABNORMAL
        """

        self._validate_number(
            "fusion_score", score, minimum=0.0
        )

        if score <= self.normal_max:
            return "NORMAL"

        if score <= self.suspicious_max:
            return "SUSPICIOUS"

        return "ABNORMAL"

    # ============================================================
    # LEGACY CONFIDENCE LABEL
    # ============================================================

    def confidence(self, score):
        """
        Retained for compatibility with existing Box 2 modules.

        LOW, MEDIUM, and HIGH represent evidence severity,
        not probabilities or calibrated classification confidence.
        """

        self._validate_number(
            "fusion_score", score, minimum=0.0
        )

        if score <= self.normal_max:
            return "LOW"

        if score <= self.suspicious_max:
            return "MEDIUM"

        return "HIGH"

    # ============================================================
    # COMPLETE FUSION
    # ============================================================

    def fuse(
        self,
        sync_score,
        physics_score,
        temporal_score,
        voltage_score,
        freshness_score=0,
    ):
        """
        Fuse available evidence channels.

        Returns the original three-key result for compatibility
        with attack classification and situation assessment.
        """

        score = self.calculate_score(
            sync_score=sync_score,
            physics_score=physics_score,
            temporal_score=temporal_score,
            voltage_score=voltage_score,
            freshness_score=freshness_score,
        )

        return {
            "fusion_score": score,
            "classification": self.classify(score),
            "confidence": self.confidence(score),
        }
