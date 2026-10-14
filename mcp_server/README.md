# Campus Customs MCP Server

This is the MCP server every agent in the Campus Customs multi-agent team uses to read and write data about the shop. Built with [FastMCP](https://gofastmcp.com).

## Database

The server only ever talks to **`data/campus_customs_new.db`**, the working copy — never the original `data/campus_customs.db`. The path comes from the `DATABASE_PATH` variable in `.env` (see `.env.example` at the project root), loaded in `config.py`. Nothing in this server hardcodes a database path.

Read-only tools use `read_only_connection()` (`mode=ro`). The new write tools use `write_connection()`, a separate helper that still only ever opens `DATABASE_PATH` — never the original database — just without `mode=ro`. All SQL everywhere is parameterized.

At startup the server idempotently creates two new tables (`CREATE TABLE IF NOT EXISTS`, so `scripts/reset_db.py` resetting the working copy is harmless): `drafts` (purchase-order and customer-message drafts) and `pending_approvals` (payment requests awaiting human sign-off).

## Tools (13 total: 8 read, 5 write)

| Tool | Read/Write | Table(s) touched |
|---|---|---|
| `check_stock(sku, size=None, requested_qty=None)` | read | `inventory`, `pricing` |
| `check_vendor_status(vendor_id=None, vendor_name=None)` | read | `vendors`, `invoices` |
| `check_lease_and_cash(lease_id)` | read | `leases`, `cash_accounts`, `desk` |
| `list_open_tickets()` | read | `tickets` |
| `get_ticket(ticket_id)` | read | `tickets` |
| `get_invoice(invoice_id)` | read | `invoices`, `vendors` (joined) |
| `list_pending_approvals()` | read | `pending_approvals` |
| `get_cash_balance(account="checking")` | read | `cash_accounts` |
| `update_ticket_status(ticket_id, status, note)` | write | `tickets` |
| `draft_purchase_order(ticket_id, sku, size, qty, vendor_id, lead_days, estimated_cost)` | write | `drafts` |
| `draft_customer_message(ticket_id, message, facts_used)` | write | `drafts` |
| `request_payment(kind, ref_id, amount, account, ticket_id=None)` | write | `pending_approvals` (reads `cash_accounts` to validate) |
| `execute_approved_payment(approval_id, approved_by)` | write | `payments`, `cash_accounts`, `invoices`, `pending_approvals` |

`execute_approved_payment` is the only tool that moves money, and it is deliberately **not** attached to any PydanticAI agent's toolset — it's reserved for a future backend-only caller that runs after a human approves a `pending_approvals` row.

Every tool returns a clear `found: False`/`ok: False` result (with a reason) instead of guessing or raising when a sku, size, vendor, lease, ticket, invoice, or approval doesn't exist, or when a business rule (insufficient cash, invalid status) would be violated.

## Running it

```bash
cd mcp_server
../.venv/Scripts/python.exe server.py
```

This starts the server over stdio (FastMCP's default transport). In practice, the PydanticAI agents in `backend/agents/` launch it themselves as a stdio subprocess via `backend/mcp_toolset.py` — you don't need to start it by hand to run the agent team.
