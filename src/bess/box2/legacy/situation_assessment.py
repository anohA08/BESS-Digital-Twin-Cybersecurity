
"""Box 2 situation assessment: combine persistence and attack signatures.

The output ``confidence`` is an ordinal strength-of-assessment label, NOT a
calibrated probability, a safety certificate, or a sensor trust score.

No recognized signature is not evidence that the measurement is trustworthy.
"""


class SituationAssessment:
    VALID_STATES = frozenset(("NORMAL", "SUSPICIOUS", "ABNORMAL"))
    VALID_CONFIDENCE = frozenset(("LOW", "MEDIUM", "HIGH"))
    SPECIFIC_ATTACK_TYPES = frozenset((
        "SENSOR_SPOOFING", "REPLAY", "COMMUNICATION_DELAY",
        "AMBIGUOUS_SPOOFING_OR_ROLLING_REPLAY",
    ))
    NON_ATTACK_TYPES = frozenset(("NORMAL", "UNKNOWN"))
    AMBIGUOUS = "AMBIGUOUS_SPOOFING_OR_ROLLING_REPLAY"

    @staticmethod
    def _result(state, assessment, attack_type, confidence, reason):
        return {
            "situation_state": state,
            "attack_assessment": assessment,
            "suspected_attack_type": attack_type,
            "confidence": confidence,
            "reason": reason,
        }

    def assess(self, final_classification, attack_type, classifier_confidence):
        """Evaluate a persistence state plus a separately derived signature.

        ``NORMAL`` means no sustained fused anomaly; it cannot establish safety.
        ``ATTACK_DETECTED`` denotes an alert matching a specific heuristic rule,
        not forensic proof of a malicious act.
        """
        if final_classification not in self.VALID_STATES:
            raise ValueError(
                "final_classification must be NORMAL, SUSPICIOUS, or ABNORMAL."
            )
        if attack_type not in self.SPECIFIC_ATTACK_TYPES | self.NON_ATTACK_TYPES:
            raise ValueError(f"Unrecognized attack_type: {attack_type!r}")
        if classifier_confidence not in self.VALID_CONFIDENCE:
            raise ValueError(
                "classifier_confidence must be LOW, MEDIUM, or HIGH."
            )

        is_specific = attack_type in self.SPECIFIC_ATTACK_TYPES
        is_ambiguous = attack_type == self.AMBIGUOUS

        if final_classification == "NORMAL":
            reason = (
                "Persistent evidence is normal; no attack is confirmed. "
                "This does not establish measurement integrity or safety."
            )
            if is_specific:
                reason += (
                    " An attack-like signature was present but not corroborated "
                    "by persistence; investigate this disagreement."
                )
            return self._result(
                "NORMAL", "NO_ATTACK_DETECTED", "NORMAL", "LOW", reason
            )

        if final_classification == "SUSPICIOUS":
            if is_specific:
                return self._result(
                    "SUSPICIOUS", "ATTACK_SUSPECTED", attack_type,
                    "LOW" if is_ambiguous or classifier_confidence == "LOW"
                    else "MEDIUM",
                    "An attack-like pattern accompanies suspicious evidence, "
                    "but the persistence criterion has not been met."
                )
            return self._result(
                "SUSPICIOUS", "UNEXPLAINED_ANOMALY", "UNKNOWN", "LOW",
                "Suspicious evidence exists without a recognized attack "
                "signature; do not treat the measurement as verified safe."
            )

        # ABNORMAL: sustained anomaly, independent of classifier label.
        if is_specific:
            if is_ambiguous:
                return self._result(
                    "ABNORMAL", "ATTACK_SUSPECTED", attack_type, "MEDIUM",
                    "Persistent abnormal evidence and an ambiguous attack-like "
                    "signature are present; the attack type is unresolved."
                )
            return self._result(
                "ABNORMAL", "ATTACK_DETECTED", attack_type,
                "HIGH" if classifier_confidence == "HIGH" else "MEDIUM",
                "Persistent abnormal evidence matches a specific modeled "
                "attack signature; this is an operational alert, not proof "
                "of malicious intent."
            )
        return self._result(
            "ABNORMAL", "UNEXPLAINED_ANOMALY", "UNKNOWN", "MEDIUM",
            "Persistent abnormal evidence is present without a recognized "
            "attack signature; model mismatch or a novel attack is possible."
        )
