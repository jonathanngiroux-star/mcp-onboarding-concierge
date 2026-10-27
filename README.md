# mcp-onboarding-concierge

MCP server for Onboarding & Migration Concierge - create checklists, track status, generate acceptance criteria.

## Tools

### create_onboarding_checklist
Create onboarding checklist for new account.

**Parameters:**
- `account_id` (string, required): Account identifier
- `account_name` (string, required): Account name
- `tier` (string, required): "basic", "professional", "enterprise", or "midband"
- `migration_from` (string, optional): System being migrated from

### get_onboarding_status
Get onboarding status for an account.

**Parameters:**
- `onboarding_id` (string, optional): Onboarding ID
- `account_id` (string, optional): Account ID (alternative)

### generate_acceptance_checklist
Generate acceptance checklist for go-live.

**Parameters:**
- `onboarding_id` (string, required): Onboarding ID
- `tier` (string, required): "basic", "professional", "enterprise", or "midband"

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Connecting to Claude Desktop

```json
{
  "mcpServers": {
    "onboarding-concierge": {
      "command": "python",
      "args": ["/path/to/mcp-onboarding-concierge/main.py"],
      "cwd": "/path/to/mcp-onboarding-concierge"
    }
  }
}
```

## License

MIT