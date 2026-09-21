"""Prometheus-style text metrics helper for the local prototype."""


class SystemMetricsCollector:
    def __init__(self):
        self.system_name = "clinical-billing-cdi-agent"
        self.tasks_total = 0
        self.critical_alerts_total = 0
        self.elevated_alerts_total = 0
        self.routine_tasks_total = 0
        self.identifier_guard_blocks_total = 0
        self.audit_blocks_total = 0
        self.processing_latency_sum = 0.0

    @property
    def phi_blocks_total(self):
        """Compatibility alias for the older metric attribute name."""
        return self.identifier_guard_blocks_total

    def record_task(self, urgency: str, duration_sec: float):
        self.tasks_total += 1
        self.processing_latency_sum += duration_sec
        self.audit_blocks_total += 1
        urgency_upper = str(urgency).upper()
        if "CRITICAL" in urgency_upper:
            self.critical_alerts_total += 1
        elif "ELEVATED" in urgency_upper:
            self.elevated_alerts_total += 1
        else:
            self.routine_tasks_total += 1

    def record_phi_block(self):
        """Compatibility method: records a configured identifier-pattern block."""
        self.identifier_guard_blocks_total += 1

    def export_prometheus_text(self) -> str:
        average_latency = self.processing_latency_sum / max(1, self.tasks_total)
        system = self.system_name
        lines = [
            "# HELP system_tasks_total Total prototype tasks processed",
            "# TYPE system_tasks_total counter",
            f'system_tasks_total{{system="{system}"}} {self.tasks_total}',
            "",
            "# HELP alerts_triggered_total Total rule alerts by urgency tier",
            "# TYPE alerts_triggered_total counter",
            f'alerts_triggered_total{{system="{system}",urgency="CRITICAL_STAT"}} {self.critical_alerts_total}',
            f'alerts_triggered_total{{system="{system}",urgency="ELEVATED_RISK"}} {self.elevated_alerts_total}',
            f'alerts_triggered_total{{system="{system}",urgency="ROUTINE"}} {self.routine_tasks_total}',
            "",
            "# HELP identifier_guard_blocks_total Configured identifier-pattern blocks",
            "# TYPE identifier_guard_blocks_total counter",
            f'identifier_guard_blocks_total{{system="{system}"}} {self.identifier_guard_blocks_total}',
            "",
            "# HELP audit_chain_blocks_total Total in-memory HMAC audit records",
            "# TYPE audit_chain_blocks_total counter",
            f'audit_chain_blocks_total{{system="{system}"}} {self.audit_blocks_total}',
            "",
            "# HELP task_processing_duration_avg_seconds Average task evaluation latency",
            "# TYPE task_processing_duration_avg_seconds gauge",
            f'task_processing_duration_avg_seconds{{system="{system}"}} {average_latency:.4f}',
            "",
        ]
        return "\n".join(lines)


GLOBAL_METRICS = SystemMetricsCollector()
