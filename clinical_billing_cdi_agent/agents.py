"""Coordinator and rule adapters for the deterministic CDI workflow prototype."""
import uuid
from typing import Any, Dict, List

from .engine import ClinicalDomainEngine
from .models import AgentAlert, ClinicalCasePayload, ClinicalIntegrityStatus, UrgencyLevel


class DocumentationGapScannerAgent:
    def audit(self, case: ClinicalCasePayload) -> List[AgentAlert]:
        result = ClinicalDomainEngine.evaluate_primary_index(case.primary_metric)
        if not result:
            return []
        return [AgentAlert(
            alert_id=str(uuid.uuid4())[:8],
            sub_agent="DocumentationGapScannerAgent",
            urgency=UrgencyLevel.WARNING,
            title=result["title"],
            clinical_finding=result["finding"],
            actionable_recommendation=result["recommendation"],
            guideline_citation="Configured demonstration rule",
        )]


class HCCRiskWeightCalculatorAgent:
    """Legacy class name retained for compatibility; no HCC weight is calculated."""

    def audit(self, case: ClinicalCasePayload) -> List[AgentAlert]:
        result = ClinicalDomainEngine.evaluate_secondary_kinetics(case.secondary_metric, case.is_stat)
        if not result:
            return []
        return [AgentAlert(
            alert_id=str(uuid.uuid4())[:8],
            sub_agent="HCCRiskWeightCalculatorAgent",
            urgency=UrgencyLevel.STAT_CRITICAL if case.is_stat else UrgencyLevel.WARNING,
            title=result["title"],
            clinical_finding=result["finding"],
            actionable_recommendation=result["recommendation"],
            guideline_citation="Configured demonstration rule",
        )]


class PhysicianQuerySynthesizerAgent:
    """Legacy class name retained for compatibility; no physician query is synthesized."""

    def audit(self, case: ClinicalCasePayload) -> List[AgentAlert]:
        result = ClinicalDomainEngine.evaluate_biomarker_concordance(case.status_flag, case.biomarkers)
        if not result:
            return []
        return [AgentAlert(
            alert_id=str(uuid.uuid4())[:8],
            sub_agent="PhysicianQuerySynthesizerAgent",
            urgency=UrgencyLevel.ADVISORY,
            title=result["title"],
            clinical_finding=result["finding"],
            actionable_recommendation=result["recommendation"],
            guideline_citation="Configured demonstration rule",
        )]


class CDICoordinator:
    def __init__(self):
        self.agent_1 = DocumentationGapScannerAgent()
        self.agent_2 = HCCRiskWeightCalculatorAgent()
        self.agent_3 = PhysicianQuerySynthesizerAgent()
        self.case_registry: Dict[str, Dict[str, Any]] = {}

    def process_case(self, case: ClinicalCasePayload) -> Dict[str, Any]:
        all_alerts: List[AgentAlert] = []
        all_alerts.extend(self.agent_1.audit(case))
        all_alerts.extend(self.agent_2.audit(case))
        all_alerts.extend(self.agent_3.audit(case))

        stat_count = sum(1 for alert in all_alerts if alert.urgency == UrgencyLevel.STAT_CRITICAL)
        warning_count = sum(1 for alert in all_alerts if alert.urgency == UrgencyLevel.WARNING)

        if stat_count:
            status = ClinicalIntegrityStatus.CRITICAL_ACTION_REQUIRED
        elif all_alerts:
            status = ClinicalIntegrityStatus.DISCORDANCE_DETECTED
        else:
            status = ClinicalIntegrityStatus.CONCORDANT_NORMAL

        dossier = {
            "system": "clinical-billing-cdi-agent",
            "domain": "Clinical documentation workflow demonstration",
            "case_id": case.case_id,
            "patient_synthetic_id": case.patient_synthetic_id,
            "overall_status": status.value,
            "total_alerts": len(all_alerts),
            "stat_critical_alerts": stat_count,
            "warning_alerts": warning_count,
            "alerts": [alert.to_dict() for alert in all_alerts],
            "guideline_standard": "No clinical guideline implemented",
            "consensus_summary": (
                f"Deterministic rules evaluated with status [{status.value}]. "
                "Human validation is required before clinical, coding, or reimbursement use."
            ),
        }
        self.case_registry[case.case_id] = dossier
        return dossier

    def query_supervisory_chat(self, user_query: str) -> str:
        query = user_query.strip().lower()
        if "status" in query or "summary" in query:
            return f"Prototype currently holds {len(self.case_registry)} case result(s) in process memory."
        if "guideline" in query or "standard" in query:
            return "No clinical guideline or CMS-HCC coefficient model is implemented; the repository uses configurable demonstration thresholds."
        return "Local deterministic prototype is available. It does not call an external language model."
