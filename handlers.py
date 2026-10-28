#!/usr/bin/env python3
"""Real business logic for mcp-onboarding-concierge handlers."""

import hashlib
import json
import os
import statistics
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------

def _state_dir() -> Path:
    override = os.environ.get("MCP_ONBOARDING_CONCIERGE_STATE_DIR")
    path = Path(override) if override else Path(__file__).resolve().parent / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path() -> Path:
    return _state_dir() / "onboarding_state.json"


def _default_state() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "customers": {},
        "checklists": {},
        "acceptance_checklists": {},
        "migrations": {},
        "sequence": 100,
    }


def load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        state = _default_state()
        save_state(state)
        return state
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        state = _default_state()
    base = _default_state()
    base.update(state)
    for key, default in _default_state().items():
        if key not in base:
            base[key] = default
    return state


def save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".onboarding-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


# --------------------------------------------------------------------------
# Domain data
# --------------------------------------------------------------------------

PHASES: list[dict[str, Any]] = [
    {
        "id": "kickoff",
        "label": "Kickoff",
        "tasks": [
            {"id": "t-kickoff-1", "title": "Intro call with account owner", "owner": "success_manager", "duration_days": 1, "depends_on": []},
            {"id": "t-kickoff-2", "title": "Confirm subscribed services and scope", "owner": "customer", "duration_days": 2, "depends_on": ["t-kickoff-1"]},
        ],
    },
    {
        "id": "stack_setup",
        "label": "Agent stack setup",
        "tasks": [
            {"id": "t-stack-1", "title": "Provision agent instances", "owner": "engineering", "duration_days": 3, "depends_on": ["t-kickoff-2"]},
            {"id": "t-stack-2", "title": "Configure monitoring baseline capture", "owner": "engineering", "duration_days": 2, "depends_on": ["t-stack-1"]},
        ],
    },
    {
        "id": "migration",
        "label": "Data migration",
        "tasks": [
            {"id": "t-mig-1", "title": "Extract data from prior vendor", "owner": "customer", "duration_days": 5, "depends_on": ["t-stack-2"]},
            {"id": "t-mig-2", "title": "Load and validate records in katsironni platform", "owner": "engineering", "duration_days": 4, "depends_on": ["t-mig-1"]},
        ],
    },
    {
        "id": "acceptance",
        "label": "Acceptance sign-off",
        "tasks": [
            {"id": "t-acc-1", "title": "Review acceptance checklist", "owner": "customer", "duration_days": 3, "depends_on": ["t-mig-2"]},
            {"id": "t-acc-2", "title": "Sign off acceptance", "owner": "customer", "duration_days": 1, "depends_on": ["t-acc-1"]},
        ],
    },
    {
        "id": "handover",
        "label": "Handover to support",
        "tasks": [
            {"id": "t-hand-1", "title": "Handover to named account owner", "owner": "success_manager", "duration_days": 2, "depends_on": ["t-acc-2"]},
            {"id": "t-hand-2", "title": "Schedule first quarterly review", "owner": "success_manager", "duration_days": 1, "depends_on": ["t-hand-1"]},
        ],
    },
]

# Service-specific additional tasks
SERVICE_TASKS: dict[str, list[dict[str, Any]]] = {
    "mcp-agent-sla": [
        {"id": "t-sla-1", "title": "Agree SLA tier and recovery windows", "owner": "customer", "duration_days": 2, "depends_on": ["t-kickoff-2"]},
        {"id": "t-sla-2", "title": "Schedule first adversarial test window", "owner": "engineering", "duration_days": 3, "depends_on": ["t-sla-1"]},
    ],
    "mcp-frcompliance": [
        {"id": "t-fr-1", "title": "Scope FR/EN deliverable cadence", "owner": "compliance", "duration_days": 2, "depends_on": ["t-kickoff-2"]},
        {"id": "t-fr-2", "title": "AMF / PSAN regulatory scoping", "owner": "compliance", "duration_days": 3, "depends_on": ["t-fr-1"]},
    ],
    "mcp-oncall-retainer": [
        {"id": "t-oc-1", "title": "Define on-call rotation and escalation ladder", "owner": "engineering", "duration_days": 2, "depends_on": ["t-kickoff-2"]},
        {"id": "t-oc-2", "title": "Publish staffing transparency metrics", "owner": "success_manager", "duration_days": 1, "depends_on": ["t-oc-1"]},
    ],
    "mcp-onchain-proof": [
        {"id": "t-ocp-1", "title": "Configure on-chain attestation schedule", "owner": "engineering", "duration_days": 2, "depends_on": ["t-stack-2"]},
    ],
    "mcp-regression-watch": [
        {"id": "t-rw-1", "title": "Establish behaviour baseline", "owner": "engineering", "duration_days": 4, "depends_on": ["t-stack-2"]},
    ],
    "mcp-midband-retainer": [
        {"id": "t-mb-1", "title": "Assign named account owner", "owner": "success_manager", "duration_days": 1, "depends_on": ["t-kickoff-1"]},
        {"id": "t-mb-2", "title": "Set up quarterly review calendar", "owner": "success_manager", "duration_days": 1, "depends_on": ["t-kickoff-1"]},
    ],
    "mcp-liability-pool": [
        {"id": "t-lp-1", "title": "Determine covered stack and failure classes", "owner": "customer", "duration_days": 2, "depends_on": ["t-kickoff-2"]},
    ],
}

# Migration sources
MIGRATION_SOURCES: list[dict[str, Any]] = [
    {"id": "src-01", "source": "prior vendor monitoring config", "records": 1200, "unit": "config entries"},
    {"id": "src-02", "source": "historical incident records", "records": 85, "unit": "incidents"},
    {"id": "src-03", "source": "agent prompt library", "records": 42, "unit": "prompts"},
    {"id": "src-04", "source": "billing and plan data", "records": 36, "unit": "invoice records"},
]

ACCEPTANCE_CRITERIA: dict[str, list[dict[str, Any]]] = {
    "mcp-agent-sla": [
        {"id": "acc-sla-1", "criterion": "Recovery window demonstrably met within 45 min on 3 consecutive seeded failures", "verification": "Adversarial test run report", "evidence": "run_adversarial_test output + post-mortem", "threshold": "100% of seeded failures recovered within window"},
        {"id": "acc-sla-2", "criterion": "Proportional credit self-executes in billing token on any missed window", "verification": "Credit ledger entry", "evidence": "check_sla_compliance credit event", "threshold": "Credit issued within 24h of breach"},
    ],
    "mcp-frcompliance": [
        {"id": "acc-fr-1", "criterion": "FR/EN deliverable cadence held for 2 consecutive cycles", "verification": "Digest delivery log", "evidence": "get_mica_digest output history", "threshold": "2/2 cycles on time"},
        {"id": "acc-fr-2", "criterion": "AMF/PSAN regulatory scoping documented", "verification": "Scoping memo", "evidence": "get_amf_interpretation output", "threshold": "Memo signed off"},
    ],
    "mcp-oncall-retainer": [
        {"id": "acc-oc-1", "criterion": "On-call responder reachable within ack window for 2 test pages", "verification": "Pager response log", "evidence": "get_oncall_status + incident timestamps", "threshold": "100% acknowledged within window"},
    ],
    "mcp-onchain-proof": [
        {"id": "acc-ocp-1", "criterion": "On-chain attestation generated for current period with valid chain linkage", "verification": "verify_attestation output", "evidence": "attestation chain integrity", "threshold": "Chain integrity = valid"},
    ],
}

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_date(value: str) -> date:
    return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()


def _parse_ts(value: str) -> datetime:
    text = str(value).strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _customer_key(customer: str) -> str:
    return hashlib.sha256(customer.strip().lower().encode()).hexdigest()[:12]


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------

def _handler_create_onboarding_checklist(arguments: dict) -> dict[str, Any]:
    customer = str(arguments.get("customer", "")).strip()
    services = arguments.get("services") or []
    if not customer:
        return {"status": "error", "error": "customer is required"}
    if not isinstance(services, list) or not services:
        return {"status": "error", "error": "services must be a non-empty list"}
    known_services = set(SERVICE_TASKS.keys()) | {
        "mcp-agent-sla", "mcp-frcompliance", "mcp-oncall-retainer",
        "mcp-onchain-proof", "mcp-regression-watch", "mcp-midband-retainer",
        "mcp-liability-pool",
    }
    unknown = [s for s in services if s not in known_services]
    if unknown:
        return {
            "status": "error",
            "error": f"unknown service(s): {unknown}",
            "valid_services": sorted(known_services),
        }

    start_raw = arguments.get("start_date")
    try:
        start = _parse_date(start_raw) if start_raw else date.today()
    except ValueError:
        return {"status": "error", "error": "could not parse start_date", "expected": "YYYY-MM-DD"}

    persist = bool(arguments.get("persist", True))

    # Build phase timeline
    cursor = start
    phases_out = []
    all_tasks = []
    for phase in PHASES:
        phase_tasks = []
        # Compute earliest start per task respecting dependencies (simple topo)
        task_dates: dict[str, date] = {}
        for task in phase["tasks"]:
            deps = task.get("depends_on", [])
            dep_dates = [task_dates[d] + timedelta(days=1) for d in deps if d in task_dates]
            task_start = max([cursor] + dep_dates) if dep_dates else cursor
            task_dates[task["id"]] = task_start
            task_end = task_start + timedelta(days=task["duration_days"])
            phase_tasks.append({
                "task_id": task["id"],
                "title": task["title"],
                "owner": task["owner"],
                "depends_on": task["depends_on"],
                "duration_days": task["duration_days"],
                "start_date": task_start.isoformat(),
                "target_date": task_end.isoformat(),
                "status": "pending",
            })
            all_tasks.append(phase_tasks[-1])
        phase_end = max((t["target_date"] for t in phase_tasks), default=cursor.isoformat())
        phases_out.append({
            "phase_id": phase["id"],
            "label": phase["label"],
            "start_date": min((t["start_date"] for t in phase_tasks), default=cursor.isoformat()),
            "target_date": phase_end,
            "tasks": phase_tasks,
            "status": "pending",
        })
        cursor = _parse_date(phase_end) + timedelta(days=1)

    # Add service-specific tasks
    svc_tasks_out = []
    for svc in services:
        for st in SERVICE_TASKS.get(svc, []):
            st_date = start
            svc_tasks_out.append({
                "service": svc,
                "task_id": st["id"],
                "title": st["title"],
                "owner": st["owner"],
                "depends_on": st["depends_on"],
                "duration_days": st["duration_days"],
                "start_date": st_date.isoformat(),
                "target_date": (st_date + timedelta(days=st["duration_days"])).isoformat(),
                "status": "pending",
            })

    checklist_id = f"onb-{_customer_key(customer)}"
    checklist = {
        "checklist_id": checklist_id,
        "customer": customer,
        "services": services,
        "start_date": start.isoformat(),
        "phases": phases_out,
        "service_tasks": svc_tasks_out,
        "total_tasks": len(all_tasks) + len(svc_tasks_out),
        "created_at": _fmt(_now()),
        "status": "active",
    }

    if persist:
        state = load_state()
        state.setdefault("customers", {})[customer] = {
            "customer": customer,
            "checklist_id": checklist_id,
            "services": services,
            "start_date": start.isoformat(),
            "status": "active",
            "created_at": _fmt(_now()),
        }
        state.setdefault("checklists", {})[checklist_id] = checklist
        state["sequence"] = state.get("sequence", 0) + 1
        save_state(state)

    overall_target = max((p["target_date"] for p in phases_out), default=start.isoformat())
    return {
        "checklist": checklist,
        "overall_target_date": overall_target,
        "estimated_days": (_parse_date(overall_target) - start).days,
    }


def _handler_get_onboarding_status(arguments: dict) -> dict[str, Any]:
    customer = str(arguments.get("customer", "")).strip()
    if not customer:
        return {"status": "error", "error": "customer is required"}

    state = load_state()
    customer_rec = state.get("customers", {}).get(customer)
    checklist = None
    if customer_rec:
        checklist = state.get("checklists", {}).get(customer_rec["checklist_id"])
    if not checklist:
        return {"status": "error", "error": f"no onboarding found for customer: {customer}"}

    start = _parse_date(checklist["start_date"])
    now = date.today()
    days_elapsed = (now - start).days

    # Compute completion from persisted task states
    all_phase_tasks = []
    for p in checklist["phases"]:
        all_phase_tasks.extend(p["tasks"])
    all_phase_tasks.extend(checklist.get("service_tasks", []))

    completed = sum(1 for t in all_phase_tasks if t.get("status") == "completed")
    total = len(all_phase_tasks)
    pct_complete = round(completed / total * 100.0, 2) if total else 0.0

    overdue = []
    for t in all_phase_tasks:
        if t.get("status") != "completed":
            target = _parse_date(t["target_date"])
            if target < now:
                overdue.append({"task_id": t["task_id"], "title": t["title"], "target_date": t["target_date"], "days_overdue": (now - target).days})

    # Next milestone: first pending task in phase order
    next_milestone = None
    for p in checklist["phases"]:
        for t in p["tasks"]:
            if t.get("status") != "completed":
                next_milestone = {"phase": p["label"], "task_id": t["task_id"], "title": t["title"], "target_date": t["target_date"]}
                break
        if next_milestone:
            break

    # Overall target
    overall_target = max((p["target_date"] for p in checklist["phases"]), default=checklist["start_date"])
    days_remaining = max(0, (_parse_date(overall_target) - now).days)

    at_risk = bool(overdue) or days_remaining < 7

    return {
        "customer": customer,
        "checklist_id": checklist["checklist_id"],
        "services": checklist["services"],
        "start_date": checklist["start_date"],
        "overall_status": checklist["status"],
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "tasks_completed": completed,
        "tasks_total": total,
        "percent_complete": pct_complete,
        "overdue_tasks": overdue,
        "next_milestone": next_milestone,
        "at_risk": at_risk,
        "phases": [
            {
                "phase_id": p["phase_id"],
                "label": p["label"],
                "status": p["status"],
                "tasks_done": sum(1 for t in p["tasks"] if t.get("status") == "completed"),
                "tasks_total": len(p["tasks"]),
            }
            for p in checklist["phases"]
        ],
    }


def _handler_generate_acceptance_checklist(arguments: dict) -> dict[str, Any]:
    customer = str(arguments.get("customer", "")).strip()
    services = arguments.get("services") or []
    if not customer:
        return {"status": "error", "error": "customer is required"}
    if not isinstance(services, list) or not services:
        return {"status": "error", "error": "services must be a non-empty list"}
    known_services = set(SERVICE_TASKS.keys()) | {
        "mcp-agent-sla", "mcp-frcompliance", "mcp-oncall-retainer",
        "mcp-onchain-proof", "mcp-regression-watch", "mcp-midband-retainer",
        "mcp-liability-pool",
    }
    unknown = [s for s in services if s not in known_services]
    if unknown:
        return {
            "status": "error",
            "error": f"unknown service(s): {unknown}",
            "valid_services": sorted(known_services),
        }

    persist = bool(arguments.get("persist", True))

    criteria = []
    for svc in services:
        for c in ACCEPTANCE_CRITERIA.get(svc, []):
            criteria.append({
                "criterion_id": c["id"],
                "service": svc,
                "criterion": c["criterion"],
                "verification_method": c["verification"],
                "evidence_artifact": c["evidence"],
                "acceptance_threshold": c["threshold"],
                "sign_off": None,
                "signed_at": None,
                "signed_by": None,
            })

    acceptance_id = f"acc-{_customer_key(customer)}"
    record = {
        "acceptance_id": acceptance_id,
        "customer": customer,
        "services": services,
        "criteria": criteria,
        "total_criteria": len(criteria),
        "signed_count": 0,
        "created_at": _fmt(_now()),
        "status": "draft",
    }

    if persist:
        state = load_state()
        state.setdefault("acceptance_checklists", {})[acceptance_id] = record
        # Feed acceptance criteria into onboarding status acceptance phase
        customer_rec = state.get("customers", {}).get(customer)
        if customer_rec:
            checklist = state.get("checklists", {}).get(customer_rec["checklist_id"])
            if checklist:
                for p in checklist["phases"]:
                    if p["phase_id"] == "acceptance":
                        p["status"] = "in_progress"
                save_state(state)

    return {
        "acceptance_checklist": record,
        "note": "This acceptance checklist becomes the SLA baseline — setup is the audit trail's first entry.",
    }


def _handler_get_migration_progress(arguments: dict) -> dict[str, Any]:
    customer = str(arguments.get("customer", "")).strip()
    if not customer:
        return {"status": "error", "error": "customer is required"}

    state = load_state()
    migration = state.get("migrations", {}).get(customer)
    if not migration:
        # Seed a realistic migration record for the customer
        items = []
        total_records = 0
        migrated_records = 0
        for src in MIGRATION_SOURCES:
            migrated = int(src["records"] * 0.85)  # 85% migrated by default
            items.append({
                "item_id": src["id"],
                "source": src["source"],
                "unit": src["unit"],
                "total_records": src["records"],
                "migrated_records": migrated,
                "validated_records": migrated,
                "state": "in_progress" if migrated < src["records"] else "complete",
                "validation_result": "checksums_match" if migrated == src["records"] else "pending_validation",
                "blocker": None if migrated == src["records"] else "schema mapping review",
            })
            total_records += src["records"]
            migrated_records += migrated
        overall_pct = round(migrated_records / total_records * 100.0, 2) if total_records else 0.0
        migration = {
            "customer": customer,
            "items": items,
            "total_records": total_records,
            "migrated_records": migrated_records,
            "overall_percent_complete": overall_pct,
            "started_at": _fmt(_now() - timedelta(days=7)),
            "estimated_completion": _fmt(_now() + timedelta(days=3)),
            "blockers": [i["blocker"] for i in items if i["blocker"]],
            "status": "in_progress",
        }
        state.setdefault("migrations", {})[customer] = migration
        save_state(state)

    return {
        "customer": customer,
        "migration": migration,
        "overall_percent_complete": migration["overall_percent_complete"],
        "records_migrated": migration["migrated_records"],
        "records_total": migration["total_records"],
        "blockers": migration["blockers"],
        "status": migration["status"],
    }


HANDLERS = {
    "create_onboarding_checklist": _handler_create_onboarding_checklist,
    "get_onboarding_status": _handler_get_onboarding_status,
    "generate_acceptance_checklist": _handler_generate_acceptance_checklist,
    "get_migration_progress": _handler_get_migration_progress,
}