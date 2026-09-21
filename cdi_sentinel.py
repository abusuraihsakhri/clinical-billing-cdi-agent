#!/usr/bin/env python3
"""Compatibility facade for the earlier cdi_sentinel.py interface.

The canonical implementation lives in the clinical_billing_cdi_agent package.
This module keeps the older public classes and CLI entry point working without
maintaining a second divergent rule engine.
"""
import argparse
import csv
import sys
from typing import Any, Dict, List

from clinical_billing_cdi_agent.agents import CDICoordinator as _Coordinator
from clinical_billing_cdi_agent.engine import ClinicalDomainEngine
from clinical_billing_cdi_agent.models import ClinicalCasePayload


class Severity(str):
    INFO = "INFO"
    ADVISORY = "ADVISORY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL_ACTION_REQUIRED"


class DomainKnowledgeRegistry:
    SYSTEM_VERSION = "2.1.0"
    ZERO_PHI_COMPLIANCE = False
    HIPAA_SAFE_HARBOR = "NOT_CLAIMED"


class AgentAlert:
    def __init__(self, alert_id: str, agent_name: str, severity: str, title: str, details: str, recommendation: str):
        self.alert_id = alert_id
        self.agent_name = agent_name
        self.severity = severity
        self.title = title
        self.details = details
        self.recommendation = recommendation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "agent": self.agent_name,
            "severity": self.severity,
            "title": self.title,
            "details": self.details,
            "recommendation": self.recommendation,
        }


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y", "on"}


class DocumentationGapScannerAgent:
    def evaluate(self, payload: Dict[str, Any]) -> List[AgentAlert]:
        result = ClinicalDomainEngine.evaluate_primary_index(float(payload.get("metric_primary", 15.0)))
        if not result:
            return []
        return [AgentAlert("legacy-primary", "DocumentationGapScannerAgent", Severity.WARNING, result["title"], result["finding"], result["recommendation"])]


class HCCRiskWeightCalculatorAgent:
    """Legacy class name retained for compatibility; no HCC weight is calculated."""

    def evaluate(self, payload: Dict[str, Any]) -> List[AgentAlert]:
        is_critical = _parse_bool(payload.get("critical_flag", False))
        result = ClinicalDomainEngine.evaluate_secondary_kinetics(
            float(payload.get("metric_secondary", 5.0)),
            is_critical,
        )
        if not result:
            return []
        severity = Severity.CRITICAL if is_critical else Severity.WARNING
        return [AgentAlert("legacy-secondary", "HCCRiskWeightCalculatorAgent", severity, result["title"], result["finding"], result["recommendation"])]


class PhysicianQuerySynthesizerAgent:
    """Legacy class name retained for compatibility; no query is synthesized."""

    def evaluate(self, payload: Dict[str, Any]) -> List[AgentAlert]:
        result = ClinicalDomainEngine.evaluate_biomarker_concordance(str(payload.get("status_text", "NORMAL")), {})
        if not result:
            return []
        return [AgentAlert("legacy-status", "PhysicianQuerySynthesizerAgent", Severity.ADVISORY, result["title"], result["finding"], result["recommendation"])]


class CDICoordinator:
    def __init__(self):
        self._coordinator = _Coordinator()
        self.case_registry = self._coordinator.case_registry

    def audit_case(self, case_payload: Dict[str, Any]) -> Dict[str, Any]:
        case = ClinicalCasePayload(
            case_id=str(case_payload.get("case_id") or "CASE-01"),
            patient_synthetic_id=str(case_payload.get("patient_synthetic_id") or "SYNTH-01"),
            primary_metric=float(case_payload.get("metric_primary", 15.0)),
            secondary_metric=float(case_payload.get("metric_secondary", 5.0)),
            status_flag=str(case_payload.get("status_text", "NORMAL")),
            is_stat=_parse_bool(case_payload.get("critical_flag", False)),
        )
        dossier = self._coordinator.process_case(case)
        alerts = []
        for alert in dossier["alerts"]:
            if alert["urgency"] == "STAT_CRITICAL":
                severity = Severity.CRITICAL
            elif alert["urgency"] == "WARNING":
                severity = Severity.WARNING
            else:
                severity = Severity.ADVISORY
            alerts.append({
                "alert_id": alert["alert_id"],
                "agent": alert["sub_agent"],
                "severity": severity,
                "title": alert["title"],
                "details": alert["clinical_finding"],
                "recommendation": alert["actionable_recommendation"],
            })

        if dossier["overall_status"] == "CRITICAL_ACTION_REQUIRED":
            overall_status = "CRITICAL_ACTION_REQUIRED"
        elif alerts:
            overall_status = "WARNING_ACTIVE"
        else:
            overall_status = "CONCORDANT_NORMAL"

        return {
            "system": dossier["system"],
            "domain": dossier["domain"],
            "case_id": dossier["case_id"],
            "overall_status": overall_status,
            "total_alerts": len(alerts),
            "critical_count": sum(1 for alert in alerts if alert["severity"] == Severity.CRITICAL),
            "warning_count": sum(1 for alert in alerts if alert["severity"] == Severity.WARNING),
            "alerts": alerts,
            "consensus_summary": dossier["consensus_summary"],
        }

    def query_assistant(self, user_query: str) -> str:
        return self._coordinator.query_supervisory_chat(user_query)


coordinator = CDICoordinator()


def create_app():
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel
    except ImportError:
        return None

    app = FastAPI(
        title="Clinical Billing / CDI Rule Demonstrator",
        description="Deterministic demonstration rules. Not clinical or coding guidance.",
        version="2.1.0",
    )

    class AuditRequest(BaseModel):
        case_id: str = "CASE-001"
        metric_primary: float = 15.0
        metric_secondary: float = 5.0
        critical_flag: bool = False
        status_text: str = "NORMAL"

    @app.get("/health")
    def health():
        return {"status": "HEALTHY", "version": "2.1.0"}

    @app.post("/api/audit")
    def api_audit(req: AuditRequest):
        return coordinator.audit_case(req.model_dump())

    return app


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="clinical-billing-cdi-agent",
        description="Compatibility CLI for the deterministic rule demonstrator",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Audit one demonstration case")
    audit_parser.add_argument("--case-id", default="CASE-TEST-001")
    audit_parser.add_argument("--primary", type=float, default=24.5)
    audit_parser.add_argument("--secondary", type=float, default=14.0)
    audit_parser.add_argument("--critical", action="store_true")
    audit_parser.add_argument("--status", default="DISCORDANT")

    batch_parser = subparsers.add_parser("batch", help="Batch process CSV")
    batch_parser.add_argument("-i", "--input", required=True)
    batch_parser.add_argument("-o", "--output", default="results.csv")

    chat_parser = subparsers.add_parser("chat", help="Query local status")
    chat_parser.add_argument("query", nargs="+")

    args = parser.parse_args(argv)

    if args.command == "audit":
        dossier = coordinator.audit_case({
            "case_id": args.case_id,
            "metric_primary": args.primary,
            "metric_secondary": args.secondary,
            "critical_flag": args.critical,
            "status_text": args.status,
        })
        print(f"Case {dossier['case_id']}: {dossier['overall_status']} ({dossier['total_alerts']} alerts)")
        return 0

    if args.command == "chat":
        print(coordinator.query_assistant(" ".join(args.query)))
        return 0

    if args.command == "batch":
        try:
            with open(args.input, "r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    raise ValueError("Input CSV must include a header row.")
                fieldnames = list(reader.fieldnames)
                rows = list(reader)

            out_fields = fieldnames + ["overall_status", "total_alerts", "critical_count", "consensus_summary"]
            output_rows = []
            for row in rows:
                dossier = coordinator.audit_case(dict(row))
                result = dict(row)
                result.update({
                    "overall_status": dossier["overall_status"],
                    "total_alerts": dossier["total_alerts"],
                    "critical_count": dossier["critical_count"],
                    "consensus_summary": dossier["consensus_summary"],
                })
                output_rows.append(result)

            with open(args.output, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=out_fields)
                writer.writeheader()
                writer.writerows(output_rows)
        except (OSError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

        print(f"Processed {len(output_rows)} records -> {args.output}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
