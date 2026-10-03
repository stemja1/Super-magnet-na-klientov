"""Workflow execution engine (spec §3 Phase 2: workflow builder).

A workflow is a JSON definition: ``{"steps": [ {type, ...}, ... ]}``.
Supported step types:

   - ``score``      -> compute lead score (LLM), store on lead
   - ``send_email`` -> send via Gmail connector (subject/body, lead.email)
   - ``enrich``     -> ORSR enrichment
   - ``log``        -> record a message
   - ``wait``       -> suspend the run for N hours and resume at the next step
   - ``condition``  -> field/op/value with nested ``then``/``else`` sub-steps

``wait`` is a real suspension: the engine stops at the first ``wait`` step and
returns ``status: "waiting"`` together with ``resume_at``. Calling execute again
resumes from the step after the wait, using the cursor persisted on the
``WorkflowRun`` row.

Steps are exposed through a lazy iterator keyed by their path in the definition,
which is what makes resumable execution possible without flattening nested
conditionals. The engine is deterministic and works with the mock Gmail
connector, so it stays fully testable offline.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.services.email.gmail import GmailConnector
from app.services.leads import _enrich, score_lead
from app.services.sequences import _render

# Guard against a malformed definition recursing forever through conditions.
MAX_NESTING_DEPTH = 10

StepPath = Tuple[int, ...]


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


def _iter_steps(
    steps: List[Dict[str, Any]],
    lead: Lead,
    path: StepPath = (),
    depth: int = 0,
) -> Iterator[Tuple[StepPath, Dict[str, Any]]]:
    """Yield ``(path, step)`` for every executable step, resolving conditions.

    A ``condition`` node is not executable itself: only the branch that matches
    the lead's current state is yielded, so its path stays stable across resumes
    as long as the evaluated field does not change.
    """
    if depth > MAX_NESTING_DEPTH:
        return
    for i, step in enumerate(steps or []):
        if not isinstance(step, dict):
            continue
        here = path + (i,)
        if step.get("type") == "condition":
            field = step.get("field", "score")
            value = getattr(lead, field, None)
            op = step.get("op", ">=")
            target = step.get("value", 0)
            branch = "then" if _eval_condition(value, op, target) else "else"
            yield from _iter_steps(step.get(branch, []) or [], lead, here, depth + 1)
        else:
            yield here, step


def _execute_step(
    step: Dict[str, Any],
    lead: Lead,
    db: Session,
    connector: GmailConnector,
) -> Dict[str, Any]:
    """Run a single step and return its result record."""
    t = step.get("type")

    if t == "score":
        score = score_lead(lead)
        lead.score = score
        db.commit()
        return {"type": "score", "score": score}

    if t == "send_email":
        to = lead.email or step.get("to")
        if not to:
            return {"type": "send_email", "skipped": "no email"}
        r = connector.send_email(
            to,
            _render(step.get("subject", ""), lead),
            _render(step.get("body", ""), lead),
        )
        return {
            "type": "send_email",
            "message_id": r.get("message_id"),
            "mode": r.get("mode"),
        }

    if t == "enrich":
        _enrich(lead)
        db.commit()
        return {"type": "enrich", "enriched": lead.enriched}

    if t == "log":
        return {"type": "log", "message": step.get("message", "")}

    return {"type": t or "unknown", "skipped": "unsupported step type"}


def execute_workflow(
    definition: Dict[str, Any],
    lead: Lead,
    db: Session,
    connector: Optional[GmailConnector] = None,
    resume_after: Optional[List[int]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Execute a workflow definition for one lead.

    Args:
        resume_after: path of a previously suspended ``wait`` step. Every step up
            to and including it is skipped, so execution continues right after it.

    Returns a dict with ``status`` (``completed`` | ``waiting`` | ``failed``),
    the ``steps`` executed in this call, and ``resume_after``/``resume_at`` when
    the run suspended on a ``wait``.
    """
    now = now or datetime.now(timezone.utc)
    connector = connector or GmailConnector()
    results: List[Dict[str, Any]] = []

    skip_to: Optional[StepPath] = tuple(resume_after) if resume_after else None
    skipping = skip_to is not None

    for path, step in _iter_steps(definition.get("steps", []) or [], lead):
        if skipping:
            if path == skip_to:
                skipping = False
            continue  # skip the wait step itself on resume

        if step.get("type") == "wait":
            try:
                hours = float(step.get("hours", 24) or 0)
            except (TypeError, ValueError):
                hours = 24.0
            resume_at = now + timedelta(hours=hours)
            results.append(
                {
                    "type": "wait",
                    "hours": hours,
                    "resume_at": resume_at.isoformat(),
                }
            )
            return {
                "status": "waiting",
                "steps": results,
                "resume_after": list(path),
                "resume_at": resume_at.isoformat(),
            }

        try:
            results.append(_execute_step(step, lead, db, connector))
        except Exception as exc:
            # Isolate the failure: one bad step must not corrupt the run record or
            # hide which steps already succeeded.
            results.append({"type": step.get("type"), "error": str(exc)})
            return {
                "status": "failed",
                "steps": results,
                "resume_after": None,
                "resume_at": None,
            }

    return {
        "status": "completed",
        "steps": results,
        "resume_after": None,
        "resume_at": None,
    }
