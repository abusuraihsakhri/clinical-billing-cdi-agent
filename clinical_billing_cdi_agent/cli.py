"""Command-line interface for the deterministic CDI workflow prototype."""
import argparse
import csv
import sys

from .agents import CDICoordinator
from .models import ClinicalCasePayload

coordinator = CDICoordinator()

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


def parse_float(value, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric value for {field_name}: {value!r}") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="clinical-billing-cdi-agent",
        description="Deterministic clinical documentation workflow prototype",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_audit = subparsers.add_parser("audit", help="Run a single demonstration case")
    p_audit.add_argument("--case-id", default="CASE-2026-001")
    p_audit.add_argument("--primary", type=float, default=26.2)
    p_audit.add_argument("--secondary", type=float, default=12.5)
    p_audit.add_argument("--stat", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    p_chat = subparsers.add_parser("chat", help="Query local prototype status")
    p_chat.add_argument("query", nargs="+")

    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="results.csv")

    p_serve = subparsers.add_parser("serve", help="Launch the optional FastAPI server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "audit":
        case = ClinicalCasePayload(
            case_id=args.case_id,
            patient_synthetic_id="SYNTH-PT-881",
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_flag=args.status,
            is_stat=args.stat,
        )
        dossier = coordinator.process_case(case)
        print("=" * 72)
        print("CLINICAL BILLING / CDI RULE DEMONSTRATOR")
        print(
            f"Case: {dossier['case_id']} | "
            f"Status: {dossier['overall_status']} | "
            f"Alerts: {dossier['total_alerts']}"
        )
        print("=" * 72)
        for alert in dossier["alerts"]:
            print(f"\n[{alert['urgency']}] {alert['title']}")
            print(f"Finding: {alert['clinical_finding']}")
            print(f"Action:  {alert['actionable_recommendation']}")
        print("\nPrototype only; not clinical, coding, or reimbursement guidance.")
        return 0

    if args.command == "chat":
        print(coordinator.query_supervisory_chat(" ".join(args.query)))
        return 0

    if args.command == "batch":
        try:
            with open(args.input, mode="r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames:
                    raise ValueError("Input CSV must include a header row.")
                fieldnames = list(reader.fieldnames)
                rows = list(reader)

            out_fields = fieldnames + [
                "overall_status",
                "total_alerts",
                "stat_critical_alerts",
                "consensus_summary",
            ]
            out_rows = []
            for row_number, row in enumerate(rows, start=2):
                try:
                    case = ClinicalCasePayload(
                        case_id=row.get("case_id") or "CASE-01",
                        patient_synthetic_id=row.get("patient_synthetic_id") or "SYNTH-01",
                        primary_metric=parse_float(
                            row.get("metric_primary", row.get("primary_metric", 15.0)),
                            "primary_metric",
                        ),
                        secondary_metric=parse_float(
                            row.get("metric_secondary", row.get("secondary_metric", 5.0)),
                            "secondary_metric",
                        ),
                        status_flag=row.get("status_flag", row.get("status_text", "NORMAL")),
                        is_stat=parse_bool(
                            row.get("is_stat", row.get("critical_flag", False))
                        ),
                    )
                except ValueError as exc:
                    raise ValueError(f"CSV row {row_number}: {exc}") from exc

                dossier = coordinator.process_case(case)
                result = dict(row)
                result["overall_status"] = dossier["overall_status"]
                result["total_alerts"] = dossier["total_alerts"]
                result["stat_critical_alerts"] = dossier["stat_critical_alerts"]
                result["consensus_summary"] = dossier["consensus_summary"]
                out_rows.append(result)

            with open(args.output, mode="w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=out_fields)
                writer.writeheader()
                writer.writerows(out_rows)
        except (OSError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

        print(f"Batch processed {len(out_rows)} records -> {args.output}")
        return 0

    if args.command == "serve":
        try:
            import uvicorn
            from .server import create_app
        except ImportError:
            print("FastAPI/uvicorn are optional. Install with: pip install '.[api]'")
            return 1

        app = create_app()
        if app is None:
            print("FastAPI is unavailable. Install with: pip install '.[api]'")
            return 1
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
