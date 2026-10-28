# mcp-onboarding-concierge

MCP server for **Onboarding & Migration Concierge** - white-glove subscriber onboarding: agent
stack setup, monitoring baseline capture, data migration into the katsironni platform,
acceptance-checklist authoring at day one.

Pricing: one-time setup ($200-400 pattern) + $80-150/mo maintenance continuation; concierge
tier at $99-199/mo.

## Tools

### `create_onboarding_checklist`
Generate and PERSIST a real onboarding checklist.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `customer` | string | **required** | Customer name |
| `services` | array of string | **required** | Services to onboard |
| `start_date` | string | today | ISO date to start onboarding |
| `persist` | boolean | `true` | Persist to state |

Returns phases (kickoff, stack setup, data migration, acceptance sign-off, handover) with
tasks, owners, dependencies, durations, target dates computed from start date, plus per-service
task sets derived from the requested services.

### `get_onboarding_status`
Return the real status of the persisted onboarding.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `customer` | string | **required** | Customer name |

Returns per-phase completion from actual recorded task states, overall percentage complete,
blockers, overdue tasks computed against target dates, days elapsed, estimated days remaining,
next milestone, and an at-risk verdict.

### `generate_acceptance_checklist`
Author and PERSIST a real acceptance checklist that becomes the SLA baseline.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `customer` | string | **required** | Customer name |
| `services` | array of string | **required** | Services to create acceptance criteria for |
| `persist` | boolean | `true` | Persist to state |

Returns numbered acceptance criteria per service with verification method, evidence artifact
required, acceptance threshold, and sign-off field. The checklist feeds back into
get_onboarding_status as the acceptance phase's criteria set.

### `get_migration_progress`
Return real migration progress.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `customer` | string | **required** | Customer name |

Returns per-source migration items with per-item state, records migrated, validation results,
blockers, and an overall completion percentage with a phase timeline.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

State persisted in `./state/onboarding_state.json`. Override with
`MCP_ONBOARDING_CONCIERGE_STATE_DIR`.

## Connecting to an MCP client

```json
{
  "mcpServers": {
    "onboarding-concierge": {
      "command": "python3",
      "args": ["/tmp/v3-services/mcp-onboarding-concierge/main.py"]
    }
  }
}
```

## License

MIT