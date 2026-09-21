"""Regression tests for the legacy-compatible deterministic workflow."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from agents.base import AuditLogger, AuditTrail, PHIGuard, SecurityException
from agents.models import SystemIntegrityStatus, SystemTaskPayload, UrgencyLevel
from agents.supervisor import SystemSupervisor
from agents.workers import InvariantQCWorker, ProtocolConformanceWorker, SafetyEscalationWorker
from cli import main


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive")
    PHIGuard.assert_no_phi("Synthetic specimen KEY-001")


def test_audit_trail_detects_record_tampering():
    trail = AuditTrail(secret_key="unit-test-secret")
    trail.log("tester", "test", "EVENT", {"status": "OK"})
    assert trail.verify_integrity() is True

    trail.logs[0]["event_type"] = "TAMPERED"
    assert trail.verify_integrity() is False


def test_specialized_workers():
    primary = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts = InvariantQCWorker.evaluate(primary)
    assert len(alerts) == 1
    assert alerts[0].urgency == UrgencyLevel.ELEVATED

    priority = SystemTaskPayload(
        task_id="T2",
        target_identifier="KEY-02",
        primary_metric=10.0,
        is_critical_flag=True,
    )
    alerts = SafetyEscalationWorker.evaluate(priority)
    assert len(alerts) == 1
    assert alerts[0].urgency == UrgencyLevel.CRITICAL_STAT

    status = SystemTaskPayload(
        task_id="T3",
        target_identifier="KEY-03",
        primary_metric=10.0,
        status_descriptor="DISCORDANT_ANOMALY",
    )
    assert len(ProtocolConformanceWorker.evaluate(status)) == 1


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL",
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash
    assert AuditLogger.verify_integrity() is True


def test_cli_and_batch_smoke():
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "configuration"]) == 0
    assert main(["verify-audit"]) == 0

    tmp_out = Path("tests_batch_out.csv")
    try:
        assert main(["batch", "-i", "sample.csv", "-o", str(tmp_out)]) == 0
        assert tmp_out.exists()
    finally:
        if tmp_out.exists():
            tmp_out.unlink()
