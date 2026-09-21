"""Command-line interface for the legacy-compatible deterministic workflow."""
import argparse
import csv
import sys

from agents.base import AuditLogger
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")
TRUE_VALUES = {"true", "1", "yes", "y", "on"}
FALSE_VALUES = {"false", "0", "no", "n", "off", ""}


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="clinical-billing-cdi-agent",
        description="Deterministic clinical documentation workflow prototype",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_audit = subparsers.add_parser("audit", help="Run a single demonstration task")
    p_audit.add_argument("--task-id", default="TASK-2026-001")
    p_audit.add_argument("--target", default="KEY-TARGET-01")
    p_audit.add_argument("--primary", type=float, default=28.5)
    p_audit.add_argument("--secondary", type=float, default=14.2)
    p_audit.add_argument("--critical", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    p_chat = subparsers.add_parser("chat", help="Query local prototype status")
    p_chat.add_argument("query", nargs="+")

    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="results.csv")

    subparsers.add_parser("verify-audit", help="Verify in-memory HMAC audit records")

    p_serve = subparsers.add_parser("serve", help="Launch the optional FastAPI server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "audit":
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
            is_critical_flag=args.critical,
        )
        dossier = supervisor.process_task(payload)
        print(f"Task {dossier.task_id}: {dossier.overall_urgency.value} ({dossier.total_alerts} alerts)")
        print("Prototype only; not clinical, coding, or reimbursement guidance.")
        return 0

    if args.command == "chat":
        print(supervisor.query_supervisory_chat(" ".join(args.query)))
        return 0

    if args.command == "verify-audit":
        trail = AuditLogger.get_trail()
        valid = AuditLogger.verify_integrity()
        print(f"Audit records: {len(trail)} | HMAC integrity verified: {valid}")
        return 0 if valid else 1

    if args.command == "batch":
        try:
            with open(args.input, mode="r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    raise ValueError("Input CSV must include a header row.")
                fieldnames = list(reader.fieldnames)
                rows = list(reader)

            out_fields = fieldnames + ["overall_urgency", "integrity_status", "total_alerts", "audit_hash"]
            out_rows = []
            for row_number, row in enumerate(rows, start=2):
                try:
                    raw_primary = row.get("primary_metric") or row.get("metric_primary", 15.0)
                    raw_secondary = row.get("secondary_metric") or row.get("metric_secondary", 5.0)
                    raw_critical = row.get("is_critical_flag") if "is_critical_flag" in row else row.get("is_stat", False)
                    payload = SystemTaskPayload(
                        task_id=row.get("task_id") or row.get("case_id", "TASK-01"),
                        target_identifier=row.get("target_identifier") or row.get("patient_synthetic_id", "TARGET-01"),
                        primary_metric=float(raw_primary),
                        secondary_metric=float(raw_secondary),
                        status_descriptor=row.get("status_descriptor") or row.get("status_flag", "NOMINAL"),
                        is_critical_flag=parse_bool(raw_critical),
                    )
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"CSV row {row_number}: {exc}") from exc

                dossier = supervisor.process_task(payload)
                result = dict(row)
                result["overall_urgency"] = dossier.overall_urgency.value
                result["integrity_status"] = dossier.integrity_status.value
                result["total_alerts"] = dossier.total_alerts
                result["audit_hash"] = dossier.audit_hash
                out_rows.append(result)

            with open(args.output, mode="w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=out_fields)
                writer.writeheader()
                writer.writerows(out_rows)
        except (OSError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

        print(f"Processed {len(out_rows)} records -> {args.output}")
        return 0

    if args.command == "serve":
        try:
            import uvicorn
            from agents.api import app
        except ImportError:
            print("FastAPI/uvicorn are optional. Install with: pip install '.[api]'")
            return 1
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
