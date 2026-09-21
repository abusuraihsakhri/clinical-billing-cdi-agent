"""
Security helpers, a lightweight identifier guard, and an in-memory HMAC audit trail.

The identifier guard is intentionally narrow. It catches several common direct-
identifier patterns but is not a complete HIPAA de-identification implementation.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

PHI_PATTERNS = [
    re.compile(r"\b(?:MRN|mrn)[:#\s-]*\d{4,10}\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b(?:DOB|Date of Birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE),
    re.compile(r"\b(?:Patient\s+Name|Patient)[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+\b", re.IGNORECASE),
]


class SecurityException(Exception):
    """Raised when the basic direct-identifier guard detects a blocked pattern."""


class ResourceLimitExceededException(Exception):
    """Raised when computational parameters exceed configured safety bounds."""


def assert_no_phi(text: str) -> None:
    """Reject text matching the repository's limited direct-identifier patterns."""
    if not text:
        return
    value = str(text)
    for pattern in PHI_PATTERNS:
        if pattern.search(value):
            raise SecurityException(
                "Identifier guard blocked content matching a configured sensitive-data pattern."
            )


class PHIGuard:
    @staticmethod
    def assert_no_phi(text: str) -> None:
        assert_no_phi(text)

    @staticmethod
    def redact_phi(text: str) -> str:
        result = str(text)
        for pattern in PHI_PATTERNS:
            result = pattern.sub("[REDACTED_IDENTIFIER]", result)
        return result


class AuditTrail:
    """In-memory HMAC-SHA256 chained audit records.

    If AUDIT_SECRET_KEY is not configured, an ephemeral process-local key is
    generated. That is safe for demonstrations and tests but does not provide a
    persistent audit identity across process restarts.
    """

    GENESIS = "GENESIS_BLOCK_0000000000000000"

    def __init__(self, secret_key: Optional[str] = None):
        configured_key = secret_key or os.getenv("AUDIT_SECRET_KEY")
        self.secret_key = (
            configured_key.encode("utf-8")
            if configured_key
            else secrets.token_bytes(32)
        )
        self.logs: List[Dict[str, Any]] = []

    def _signature_for(self, entry: Dict[str, Any]) -> str:
        sign_string = "|".join(
            [
                str(entry["audit_id"]),
                str(entry["timestamp"]),
                str(entry["actor"]),
                str(entry["actor_tier"]),
                str(entry["event_type"]),
                str(entry["payload_hash"]),
                str(entry["prev_hash"]),
            ]
        )
        return hmac.new(
            self.secret_key,
            sign_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def log(
        self,
        actor: str,
        actor_tier: str,
        event_type: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload_str = json.dumps(details, sort_keys=True, separators=(",", ":"))
        assert_no_phi(payload_str)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        audit_id = f"AUDIT-{int(time.time() * 1000)}-{len(self.logs) + 1}"
        timestamp = datetime.now(timezone.utc).isoformat()
        prev_hash = self.logs[-1]["current_hash"] if self.logs else self.GENESIS

        entry = {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "actor": actor,
            "actor_tier": actor_tier,
            "event_type": event_type,
            "payload_hash": payload_hash,
            "prev_hash": prev_hash,
        }
        entry["current_hash"] = self._signature_for(entry)
        self.logs.append(entry)
        return dict(entry)

    def verify_integrity(self) -> bool:
        """Verify both chain linkage and every record's HMAC signature."""
        for index, entry in enumerate(self.logs):
            expected_prev = (
                self.logs[index - 1]["current_hash"]
                if index > 0
                else self.GENESIS
            )
            if entry.get("prev_hash") != expected_prev:
                return False
            required = {
                "audit_id",
                "timestamp",
                "actor",
                "actor_tier",
                "event_type",
                "payload_hash",
                "prev_hash",
                "current_hash",
            }
            if not required.issubset(entry):
                return False
            expected_signature = self._signature_for(entry)
            if not hmac.compare_digest(
                str(entry["current_hash"]),
                expected_signature,
            ):
                return False
        return True

    def get_trail(self) -> List[Dict[str, Any]]:
        return [dict(entry) for entry in self.logs]


GLOBAL_AUDIT = AuditTrail()


class AuditLogger:
    @staticmethod
    def log(
        actor: str,
        actor_tier: str,
        event_type: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        return GLOBAL_AUDIT.log(actor, actor_tier, event_type, details)

    @staticmethod
    def get_trail() -> List[Dict[str, Any]]:
        return GLOBAL_AUDIT.get_trail()

    @staticmethod
    def verify_integrity() -> bool:
        return GLOBAL_AUDIT.verify_integrity()


class ActionExecutor:
    @staticmethod
    def execute_with_audit(
        actor: str,
        actor_tier: str,
        action_type: str,
        fn,
        *args,
        **kwargs,
    ):
        result = fn(*args, **kwargs)
        AuditLogger.log(actor, actor_tier, action_type, {"status": "SUCCESS"})
        return result
