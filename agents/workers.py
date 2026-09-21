"""Deterministic worker rules for the repository's demonstration workflow."""
import uuid
from typing import List

from .models import AgentAlert, SystemTaskPayload, UrgencyLevel


PRIMARY_ALERT_LIMIT = 25.0
SECONDARY_ALERT_LIMIT = 12.0
STATUS_KEYWORDS = ("DISCORDANT", "ANOMALY", "FAIL", "REJECT", "SUSPICIOUS")


class InvariantQCWorker:
    @classmethod
    def evaluate(cls, payload: SystemTaskPayload) -> List[AgentAlert]:
        if payload.primary_metric <= PRIMARY_ALERT_LIMIT:
            return []
        return [AgentAlert(
            alert_id=f"QC-{uuid.uuid4().hex[:6]}",
            origin_worker="InvariantQCWorker",
            urgency=UrgencyLevel.ELEVATED,
            summary="Primary metric review trigger",
            technical_details=(
                f"Primary measurement ({payload.primary_metric:.2f}) exceeds the "
                f"configured demonstration threshold ({PRIMARY_ALERT_LIMIT:.2f})."
            ),
            actionable_remediation="Review the source data and local rule configuration.",
        )]


class SafetyEscalationWorker:
    @classmethod
    def evaluate(cls, payload: SystemTaskPayload) -> List[AgentAlert]:
        if not payload.is_critical_flag and payload.secondary_metric <= SECONDARY_ALERT_LIMIT:
            return []
        return [AgentAlert(
            alert_id=f"SAFE-{uuid.uuid4().hex[:6]}",
            origin_worker="SafetyEscalationWorker",
            urgency=UrgencyLevel.CRITICAL_STAT if payload.is_critical_flag else UrgencyLevel.ELEVATED,
            summary="Priority review trigger",
            technical_details=(
                f"PriorityFlag={payload.is_critical_flag}; secondary metric="
                f"{payload.secondary_metric:.2f}; configured threshold={SECONDARY_ALERT_LIMIT:.2f}."
            ),
            actionable_remediation="Escalate for human review according to local policy.",
        )]


class ProtocolConformanceWorker:
    @classmethod
    def evaluate(cls, payload: SystemTaskPayload) -> List[AgentAlert]:
        descriptor = str(payload.status_descriptor).upper()
        if not any(keyword in descriptor for keyword in STATUS_KEYWORDS):
            return []
        return [AgentAlert(
            alert_id=f"CONF-{uuid.uuid4().hex[:6]}",
            origin_worker="ProtocolConformanceWorker",
            urgency=UrgencyLevel.ELEVATED,
            summary="Status descriptor review trigger",
            technical_details=f"Descriptor '{payload.status_descriptor}' matched a configured review keyword.",
            actionable_remediation="Verify the underlying documentation before clinical, coding, or reimbursement action.",
        )]
