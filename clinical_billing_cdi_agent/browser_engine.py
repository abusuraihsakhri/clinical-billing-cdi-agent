"""Pure-Python browser runtime for the GitHub Pages demonstration UI.

The rules are deterministic repository examples. They are not validated
clinical, coding, reimbursement, or CMS-HCC criteria.
"""
import csv
import io
import json
from typing import Any, Dict

PRIMARY_ALERT_LIMIT = 25.0
SECONDARY_ALERT_LIMIT = 12.0
STATUS_KEYWORDS = ("DISCORDANT", "ANOMALY", "EQUIVOCAL", "SUSPICIOUS", "FAIL", "REJECT")
TRUE_VALUES = {"true", "1", "yes", "y", "on"}
FALSE_VALUES = {"false", "0", "no", "n", "off", ""}


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def evaluate_case(payload: Dict[str, Any]) -> Dict[str, Any]:
    case_id = str(payload.get("case_id") or "CASE-001")
    primary = float(payload.get("primary_metric", 0))
    secondary = float(payload.get("secondary_metric", 0))
    status = str(payload.get("status_flag") or "NORMAL")
    priority = parse_bool(payload.get("is_stat", False))

    alerts = []
    if primary > PRIMARY_ALERT_LIMIT:
        alerts.append({
            "code": "PRIMARY_THRESHOLD",
            "level": "REVIEW",
            "title": "Primary metric review trigger",
            "detail": f"{primary:.2f} exceeds the configured demonstration threshold of {PRIMARY_ALERT_LIMIT:.2f}.",
        })

    if priority or secondary > SECONDARY_ALERT_LIMIT:
        alerts.append({
            "code": "PRIORITY_THRESHOLD",
            "level": "PRIORITY" if priority else "REVIEW",
            "title": "Priority review trigger",
            "detail": (
                f"Secondary metric={secondary:.2f}; priority flag={priority}; "
                f"configured threshold={SECONDARY_ALERT_LIMIT:.2f}."
            ),
        })

    upper_status = status.upper()
    if any(keyword in upper_status for keyword in STATUS_KEYWORDS):
        alerts.append({
            "code": "STATUS_KEYWORD",
            "level": "REVIEW",
            "title": "Status descriptor review trigger",
            "detail": f"'{status}' matched a configured review keyword.",
        })

    if any(alert["level"] == "PRIORITY" for alert in alerts):
        outcome = "PRIORITY_REVIEW"
    elif alerts:
        outcome = "REVIEW_RECOMMENDED"
    else:
        outcome = "NO_RULE_TRIGGERED"

    return {
        "case_id": case_id,
        "outcome": outcome,
        "alert_count": len(alerts),
        "alerts": alerts,
        "inputs": {
            "primary_metric": primary,
            "secondary_metric": secondary,
            "status_flag": status,
            "is_stat": priority,
        },
        "notice": "Prototype output only; human validation is required.",
    }


def evaluate_case_json(payload_json: str) -> str:
    return json.dumps(evaluate_case(json.loads(payload_json)))


def evaluate_csv(csv_text: str) -> str:
    source = io.StringIO(csv_text)
    reader = csv.DictReader(source)
    if not reader.fieldnames:
        raise ValueError("CSV must contain a header row.")

    output_fields = list(reader.fieldnames)
    for field in ("outcome", "alert_count"):
        if field not in output_fields:
            output_fields.append(field)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=output_fields)
    writer.writeheader()

    rows = 0
    review_rows = 0
    for row_number, row in enumerate(reader, start=2):
        try:
            result = evaluate_case({
                "case_id": row.get("case_id") or row.get("task_id") or f"ROW-{row_number}",
                "primary_metric": row.get("metric_primary") or row.get("primary_metric") or 0,
                "secondary_metric": row.get("metric_secondary") or row.get("secondary_metric") or 0,
                "status_flag": row.get("status_flag") or row.get("status_descriptor") or "NORMAL",
                "is_stat": row.get("is_stat") if "is_stat" in row else row.get("is_critical_flag", False),
            })
        except (TypeError, ValueError) as exc:
            raise ValueError(f"CSV row {row_number}: {exc}") from exc

        result_row = dict(row)
        result_row["outcome"] = result["outcome"]
        result_row["alert_count"] = result["alert_count"]
        writer.writerow(result_row)
        rows += 1
        if result["alert_count"]:
            review_rows += 1

    return json.dumps({
        "rows": rows,
        "review_rows": review_rows,
        "csv": output.getvalue(),
    })
