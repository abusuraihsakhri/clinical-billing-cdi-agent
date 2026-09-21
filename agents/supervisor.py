"""Coordinator for the legacy-compatible deterministic rule workflow."""
import uuid
from typing import Dict

from .base import AuditLogger, PHIGuard
from .llm_factory import LLMFactory
from .models import ConsensusDossier, SystemIntegrityStatus, SystemTaskPayload, UrgencyLevel
from .workers import InvariantQCWorker, ProtocolConformanceWorker, SafetyEscalationWorker


class SystemSupervisor:
    def __init__(self, model_provider: str = "mock"):
        self.qc_worker = InvariantQCWorker()
        self.safety_worker = SafetyEscalationWorker()
        self.conformance_worker = ProtocolConformanceWorker()
        self.llm = LLMFactory.create(model_provider, system_name="Clinical Billing CDI Agent")
        self.dossier_registry: Dict[str, ConsensusDossier] = {}

    def process_task(self, payload: SystemTaskPayload, actor: str = "SystemSupervisor") -> ConsensusDossier:
        PHIGuard.assert_no_phi(payload.task_id)
        PHIGuard.assert_no_phi(payload.target_identifier)
        PHIGuard.assert_no_phi(payload.status_descriptor)

        alerts = []
        alerts.extend(self.qc_worker.evaluate(payload))
        alerts.extend(self.safety_worker.evaluate(payload))
        alerts.extend(self.conformance_worker.evaluate(payload))

        critical_count = sum(1 for alert in alerts if alert.urgency == UrgencyLevel.CRITICAL_STAT)
        elevated_count = sum(1 for alert in alerts if alert.urgency == UrgencyLevel.ELEVATED)

        if critical_count:
            overall_urgency = UrgencyLevel.CRITICAL_STAT
            integrity_status = SystemIntegrityStatus.RECALIBRATION_REQUIRED
        elif elevated_count:
            overall_urgency = UrgencyLevel.ELEVATED
            integrity_status = SystemIntegrityStatus.DISCORDANT
        else:
            overall_urgency = UrgencyLevel.ROUTINE
            integrity_status = SystemIntegrityStatus.VALIDATED

        audit_entry = AuditLogger.log(
            actor=actor,
            actor_tier="supervisor",
            event_type="TASK_EVALUATION_COMPLETED",
            details={
                "task_id": payload.task_id,
                "target_identifier": payload.target_identifier,
                "overall_urgency": overall_urgency.value,
                "total_alerts": len(alerts),
            },
        )

        dossier = ConsensusDossier(
            dossier_id=f"DOSSIER-{uuid.uuid4().hex[:8].upper()}",
            task_id=payload.task_id,
            target_identifier=payload.target_identifier,
            overall_urgency=overall_urgency,
            integrity_status=integrity_status,
            total_alerts=len(alerts),
            critical_alerts_count=critical_count,
            alerts=alerts,
            consensus_summary=(
                f"Configured deterministic rules completed with status "
                f"[{overall_urgency.value}]. Total alerts: {len(alerts)}."
            ),
            audit_hash=audit_entry["current_hash"],
        )
        self.dossier_registry[dossier.dossier_id] = dossier
        return dossier

    def query_supervisory_chat(self, query: str) -> str:
        PHIGuard.assert_no_phi(query)
        return self.llm.invoke(query)
