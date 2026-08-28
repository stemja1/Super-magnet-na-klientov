"""Workflow execution engine (spec §3 Phase 2: workflow builder).

A workflow is a JSON definition: {"steps": [ {type, ...}, ... ]}.
Supported step types:
  - score            -> compute lead score (LLM), store on lead
  - send_email       -> send via Gmail connector (subject/body, lead.email)
  - enrich           -> ORSR enrichment
  - log              -> record a message
  - wait             -> record a delay (scheduling handled by Celery in prod)
  - condition        -> field/op/value, then/else sub-steps (nested)

The engine is deterministic and works with the mock Gmail connector, so it is
fully testable offline.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.services.email.gmail import GmailConnector
from app.services.leads import _enrich, score_lead


def _eval_condition(value: Any, op: str, target: Any) -> bool:
    # Numeric comparison when both sides parse as numbers.
    try:
        v = float(value)
        t = float(target)
        return {
            ">": v > t,
            ">=": v >= t,
            "<": v < t,
            "<=": v <= t,
            "==": v == t,
            "!=": v != t,
        }.get(op, False)
    except (TypeError, ValueError):
        pass
    # Fall back to string comparison (e.g. sector == "IT").
    sval, starget = str(value), str(target)
    return {
        ">": sval > starget,
        ">=": sval >= starget,
        "<": sval < starget,
        "<=": sval <= starget,
        "==": sval == starget,
        "!=": sval != starget,
    }.get(op, False)


def _run_steps(
    steps: List[Dict[str, Any]],
    lead: Lead,
    db: Session,
    connector: GmailConnector,
    results: List[Dict[str, Any]],
) -> None:
    for step in steps or []:
        t = step.get("type")
        if t == "score":
            score = score_lead(lead)
            lead.score = score
            db.commit()
            results.append({"type": "score", "score": score})
        elif t == "send_email":
            to = lead.email or step.get("to")
            if to:
                r = connector.send_email(to, step.get("subject", ""), step.get("body", ""))
                results.append(
                    {"type": "send_email", "message_id": r.get("message_id"), "mode": r.get("mode")}
                )
            else:
                results.append({"type": "send_email", "skipped": "no email"})
        elif t == "enrich":
            _enrich(lead)
            db.commit()
            results.append({"type": "enrich", "enriched": lead.enriched})
        elif t == "log":
            results.append({"type": "log", "message": step.get("message", "")})
        elif t == "wait":
            results.append({"type": "wait", "hours": step.get("hours", 24)})
        elif t == "condition":
            val = getattr(lead, step.get("field", "score"), None)
            if _eval_condition(val, step.get("op", ">="), step.get("value", 0)):
                _run_steps(step.get("then", []), lead, db, connector, results)
            else:
                _run_steps(step.get("else", []), lead, db, connector, results)


def execute_workflow(
    definition: Dict[str, Any],
    lead: Lead,
    db: Session,
    connector: Optional[GmailConnector] = None,
) -> List[Dict[str, Any]]:
    connector = connector or GmailConnector()
    results: List[Dict[str, Any]] = []
    _run_steps(definition.get("steps", []), lead, db, connector, results)
    return results
