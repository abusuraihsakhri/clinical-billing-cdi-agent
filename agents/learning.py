"""Simple feedback-based worker weighting utilities.

This module does not implement Bayesian inference or model training. It tracks
observed agreement counts and derives a bounded heuristic weight.
"""
from typing import Any, Dict, List

from pydantic import BaseModel


class WorkerPerformanceMetric(BaseModel):
    worker_name: str
    total_evaluations: int = 0
    concordant_decisions: int = 0
    historical_brier_score: float = 0.05
    dynamic_weight: float = 1.0


class ActiveLearningEngine:
    """Compatibility name for a simple feedback-weighting helper."""

    def __init__(self, system_name: str = "Clinical Billing CDI Agent"):
        self.system_name = system_name
        self.worker_metrics: Dict[str, WorkerPerformanceMetric] = {
            "InvariantQCWorker": WorkerPerformanceMetric(worker_name="InvariantQCWorker"),
            "SafetyEscalationWorker": WorkerPerformanceMetric(worker_name="SafetyEscalationWorker"),
            "ProtocolConformanceWorker": WorkerPerformanceMetric(worker_name="ProtocolConformanceWorker"),
        }
        self.uncertainty_buffer: List[Dict[str, Any]] = []

    def record_feedback(self, worker_name: str, was_concordant: bool, confidence_score: float):
        if worker_name not in self.worker_metrics:
            self.worker_metrics[worker_name] = WorkerPerformanceMetric(worker_name=worker_name)

        metric = self.worker_metrics[worker_name]
        metric.total_evaluations += 1
        if was_concordant:
            metric.concordant_decisions += 1

        agreement_rate = metric.concordant_decisions / max(1, metric.total_evaluations)
        metric.dynamic_weight = round(max(0.2, min(2.0, agreement_rate * 1.5)), 3)

        if 0.45 <= confidence_score <= 0.65:
            self.uncertainty_buffer.append({
                "worker": worker_name,
                "confidence": confidence_score,
                "concordant": was_concordant,
            })

    def get_calibrated_weights(self) -> Dict[str, float]:
        return {name: metric.dynamic_weight for name, metric in self.worker_metrics.items()}


GLOBAL_LEARNING_ENGINE = ActiveLearningEngine()
