"""Optional FastAPI application for the deterministic CDI workflow prototype."""
from typing import Any, Dict

from .agents import CDICoordinator
from .models import ClinicalCasePayload

coordinator = CDICoordinator()


def create_app():
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel, Field
    except ImportError:
        return None

    app = FastAPI(
        title="Clinical Billing / CDI Rule Demonstrator",
        description="Deterministic prototype rules; not clinical, coding, or reimbursement guidance.",
        version="2.1.0",
    )

    class AuditRequest(BaseModel):
        case_id: str = "CASE-2026-001"
        patient_synthetic_id: str = "SYNTH-PT-881"
        primary_metric: float = 24.5
        secondary_metric: float = 14.0
        status_flag: str = "DISCORDANT"
        is_stat: bool = True
        clinical_notes: str = ""
        biomarkers: Dict[str, Any] = Field(default_factory=dict)

    class ChatRequest(BaseModel):
        query: str

    @app.get("/health")
    def health():
        return {
            "status": "HEALTHY",
            "system": "clinical-billing-cdi-agent",
            "version": "2.1.0",
            "scope": "deterministic prototype",
        }

    @app.post("/api/audit")
    def api_audit(req: AuditRequest):
        return coordinator.process_case(ClinicalCasePayload(
            case_id=req.case_id,
            patient_synthetic_id=req.patient_synthetic_id,
            primary_metric=req.primary_metric,
            secondary_metric=req.secondary_metric,
            status_flag=req.status_flag,
            is_stat=req.is_stat,
            clinical_notes=req.clinical_notes,
            biomarkers=req.biomarkers,
        ))

    @app.post("/api/chat")
    def api_chat(req: ChatRequest):
        return {"response": coordinator.query_supervisory_chat(req.query)}

    return app
