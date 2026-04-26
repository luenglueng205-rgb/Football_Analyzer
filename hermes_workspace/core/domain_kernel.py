from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, List, Literal, Optional, Tuple


RoleId = Literal["router", "scout", "analyst", "risk-manager"]


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_hash(payload: Any) -> str:
    try:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        raw = repr(payload)
    return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class KernelValidation:
    ok: bool
    role: RoleId
    schema_version: str
    issues: List[Dict[str, Any]]
    validated_at: str
    payload_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "role": self.role,
            "schema_version": self.schema_version,
            "issues": list(self.issues),
            "validated_at": self.validated_at,
            "payload_hash": self.payload_hash,
        }


class DomainKernel:
    schema_version = "1.0"

    @staticmethod
    def _coerce_confidence(output: Dict[str, Any]) -> Optional[float]:
        if "confidence" not in output:
            return None
        try:
            c = float(output.get("confidence"))
        except Exception:
            return None
        if c < 0.0:
            return 0.0
        if c > 1.0:
            return 1.0
        return c

    @staticmethod
    def normalize(role: RoleId, output: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(output, dict):
            return {"status": "error", "error": {"code": "BAD_OUTPUT", "message": "output must be dict"}}

        normalized = dict(output)
        normalized.setdefault("role", role)
        normalized.setdefault("schema_version", DomainKernel.schema_version)
        normalized.setdefault("timestamp", normalized.get("timestamp") or _now_utc())
        normalized.setdefault("evidence", [])

        coerced_conf = DomainKernel._coerce_confidence(normalized)
        if coerced_conf is not None:
            normalized["confidence"] = coerced_conf

        return normalized

    @staticmethod
    def validate(role: RoleId, output: Dict[str, Any]) -> KernelValidation:
        issues: List[Dict[str, Any]] = []

        if not isinstance(output, dict):
            issues.append({"code": "BAD_TYPE", "message": "output must be dict"})
            return KernelValidation(
                ok=False,
                role=role,
                schema_version=DomainKernel.schema_version,
                issues=issues,
                validated_at=_now_utc(),
                payload_hash=_stable_hash(output),
            )

        if str(output.get("role") or "") and str(output.get("role")) != role:
            issues.append({"code": "ROLE_MISMATCH", "message": f"expected role={role}", "got": output.get("role")})

        if output.get("schema_version") and str(output.get("schema_version")) != DomainKernel.schema_version:
            issues.append(
                {
                    "code": "SCHEMA_VERSION_MISMATCH",
                    "message": f"expected schema_version={DomainKernel.schema_version}",
                    "got": output.get("schema_version"),
                }
            )

        conf = output.get("confidence")
        if conf is not None:
            try:
                cf = float(conf)
                if cf < 0.0 or cf > 1.0:
                    issues.append({"code": "BAD_CONFIDENCE", "message": "confidence must be in [0,1]"})
            except Exception:
                issues.append({"code": "BAD_CONFIDENCE", "message": "confidence must be numeric"})

        has_evidence = bool(output.get("evidence")) or bool(output.get("data_source")) or bool(output.get("tool_calls"))
        if not has_evidence:
            issues.append({"code": "NO_EVIDENCE", "message": "tool-first requirement unmet (missing evidence/data_source)"})

        if role == "router":
            decision = output.get("decision")
            if not (isinstance(decision, dict) and decision.get("action") in {"DEEP_DIVE", "IGNORE"}):
                issues.append(
                    {
                        "code": "BAD_ROUTER_DECISION",
                        "message": "router decision must be dict with action in {DEEP_DIVE,IGNORE}",
                    }
                )
        elif role == "risk-manager":
            rec = output.get("recommendation")
            if rec not in {None, "approve", "reject_and_replan", "final_reject", "skip"}:
                issues.append(
                    {
                        "code": "BAD_RISK_RECOMMENDATION",
                        "message": "risk-manager recommendation must be approve/reject_and_replan/final_reject/skip",
                    }
                )

        ok = len(issues) == 0
        return KernelValidation(
            ok=ok,
            role=role,
            schema_version=DomainKernel.schema_version,
            issues=issues,
            validated_at=_now_utc(),
            payload_hash=_stable_hash({k: v for k, v in output.items() if k not in {"timestamp", "validated_at"}}),
        )

    @staticmethod
    def attach(role: RoleId, output: Dict[str, Any]) -> Dict[str, Any]:
        normalized = DomainKernel.normalize(role, output)
        validation = DomainKernel.validate(role, normalized)
        normalized["domain_kernel"] = validation.to_dict()
        return normalized

