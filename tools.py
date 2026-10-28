#!/usr/bin/env python3
"""Tool definitions for mcp-onboarding-concierge."""

from mcp.types import Tool

TOOLS = [
    Tool(
        name="create_onboarding_checklist",
        description=(
            "Generate and PERSIST a real onboarding checklist: phases (kickoff, stack setup, "
            "monitoring baseline capture, data migration, acceptance sign-off, handover), each "
            "with concrete tasks, owners, dependencies, estimated durations, target dates "
            "computed from a start date, and a per-service task set derived from the requested "
            "services."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer": {
                    "type": "string",
                    "description": "Customer name.",
                },
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Services to onboard (e.g. mcp-agent-sla, mcp-frcompliance).",
                },
                "start_date": {
                    "type": "string",
                    "description": "ISO date to start onboarding; defaults to today.",
                },
                "persist": {"type": "boolean", "default": True},
            },
            "required": ["customer", "services"],
        },
    ),
    Tool(
        name="get_onboarding_status",
        description=(
            "Return the REAL status of the persisted onboarding: per-phase completion from the "
            "actual recorded task states, overall percentage complete, blockers, overdue tasks "
            "computed against target dates, days elapsed, estimated days remaining, next "
            "milestone, and an at-risk verdict."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer": {
                    "type": "string",
                    "description": "Customer name.",
                },
            },
            "required": ["customer"],
        },
    ),
    Tool(
        name="generate_acceptance_checklist",
        description=(
            "Author and PERSIST a real acceptance checklist that becomes the SLA baseline: "
            "numbered acceptance criteria per service with verification method, evidence "
            "artifact required, acceptance threshold, and sign-off field."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer": {
                    "type": "string",
                    "description": "Customer name.",
                },
                "services": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Services to create acceptance criteria for.",
                },
                "persist": {"type": "boolean", "default": True},
            },
            "required": ["customer", "services"],
        },
    ),
    Tool(
        name="get_migration_progress",
        description=(
            "Return REAL migration progress: per-source migration items with per-item state, "
            "records migrated, validation results, blockers, and an overall completion "
            "percentage with a phase timeline."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "customer": {
                    "type": "string",
                    "description": "Customer name.",
                },
            },
            "required": ["customer"],
        },
    ),
]