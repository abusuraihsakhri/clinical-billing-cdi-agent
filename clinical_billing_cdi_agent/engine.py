"""Deterministic demonstration rules for the clinical billing/CDI prototype.

These thresholds are repository configuration values, not validated clinical,
coding, reimbursement, or CMS-HCC criteria.
"""
from typing import Any, Dict, Optional


class ClinicalDomainEngine:
    PRIMARY_ALERT_LIMIT = 25.0
    SECONDARY_ALERT_LIMIT = 12.0
    STATUS_KEYWORDS = ("DISCORDANT", "EQUIVOCAL", "SUSPICIOUS")

    @classmethod
    def evaluate_primary_index(cls, value: float) -> Optional[Dict[str, Any]]:
        if value > cls.PRIMARY_ALERT_LIMIT:
            return {
                "title": "Primary Metric Review Trigger",
                "finding": (
                    f"Observed value ({value:.2f}) exceeds the configured "
                    f"demonstration threshold ({cls.PRIMARY_ALERT_LIMIT:.1f})."
                ),
                "recommendation": "Review the source data and the configured rule before acting.",
            }
        return None

    @classmethod
    def evaluate_secondary_kinetics(
        cls,
        value: float,
        is_stat: bool,
    ) -> Optional[Dict[str, Any]]:
        if value > cls.SECONDARY_ALERT_LIMIT or is_stat:
            return {
                "title": "Priority Review Trigger",
                "finding": (
                    f"Secondary value ({value:.2f}) and priority flag "
                    f"(is_stat={is_stat}) triggered the configured rule."
                ),
                "recommendation": "Escalate for human review according to local policy.",
            }
        return None

    @classmethod
    def evaluate_biomarker_concordance(
        cls,
        status_flag: str,
        biomarkers: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        del biomarkers
        status_upper = str(status_flag).upper()
        if any(keyword in status_upper for keyword in cls.STATUS_KEYWORDS):
            return {
                "title": "Status Descriptor Review Trigger",
                "finding": f"Status flag '{status_flag}' matches a configured review keyword.",
                "recommendation": "Verify the underlying documentation before any coding or clinical decision.",
            }
        return None
