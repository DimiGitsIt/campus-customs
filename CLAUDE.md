# Campus Customs Multi-Agent Operations — Standing Rules

## Architecture
The project has three parts:
- An MCP server
- A FastAPI backend with a multi-agent team
- A React dashboard where a human watches the agents and approves requests

## Agents
- **Boss**: reads each ticket, decides who works on it, makes final calls
- **Inventory**
- **Accounting**
- **Facilities**
- **Customer Service**: drafts customer messages

Any agent can delegate to any other agent.

## Model
Use only `gpt-6-luna` through Portkey (`PORTKEY_API_KEY`) for every agent, defined in one place (`DATABASE_PATH`/model config, see `.env.example`). No other model may appear anywhere in the code or runs.

## Business rules
- `desk.date_today` is "today" for deciding what's overdue.
- Vendor lead times come from the `vendors` table. A vendor won't ship while they have an open unpaid invoice.
- Any payment requires human approval, and when a payment is made the relevant table must be updated. The pay tool must refuse if there isn't enough cash (no negative balances). Cash only goes out; no money comes in.
- Never email customers or call real vendors. Drafts stay on the board.

## Database
- Only touch `campus_customs_new.db`. Never modify `campus_customs.db`.
- Both `data/campus_customs.db` and `data/campus_customs_new.db` ARE committed (as of Problem 11), so graders can clone and run the app without needing the original zip. `campus_customs_new.db` is committed in its post-run state, not reset, so its `cash_accounts` balance matches what `output/desk_tickets.html`'s Cash tab reports.
- Never commit `.env` or anything else under `data/` besides the two `.db` files.
