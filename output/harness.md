# Campus Customs — Data Harness

This file documents what every field in `data/campus_customs.db` is for, from the point of view of the humans and agents who will use it (Boss, Inventory, Accounting, Facilities, Customer Service). New sections get appended as later problems add tools, specs, and safety notes.

---

## desk

| Field | Why it matters |
|---|---|
| date_today | The agents' notion of "today." Used to decide what's overdue (invoices, rent, lead times) instead of the real system clock. |
| notes | Freeform desk notes for the human; not read by any business logic. |

## inventory

| Field | Why it matters |
|---|---|
| sku | Identifies the product line; joins to `pricing.sku` and to `tickets.sku`. |
| name | Human-readable product name for tickets, dashboards, and customer drafts. |
| size | Inventory is tracked per size, so Inventory must match both sku **and** size to know what's actually in stock. |
| qty | The number Inventory checks against a ticket's requested qty to spot a shortfall. |
| location | Tells Inventory/Facilities where to physically pull stock from; not needed for restock decisions. |

## pricing

| Field | Why it matters |
|---|---|
| sku | Joins to `inventory.sku`; one row per sku (not per size), so price doesn't vary by size. |
| unit_cost | What Accounting needs to value a restock order or discount's margin impact. |
| list_price | What Accounting/Boss compares against any requested discount (e.g. a price-override ticket) to see how much margin is being given up. |

## vendors

| Field | Why it matters |
|---|---|
| id | Joins to `invoices.vendor_id`; the only way to tie an open bill back to a specific vendor. |
| name | Identifies the vendor in tickets/drafts (never contacted directly — drafts only). |
| specialty | Tells Boss/Inventory which vendor is the right fit for a given sku's restock (e.g. apparel reprint vs. mugs vs. courier). |
| lead_days | How long Inventory/Boss should expect to wait for stock to arrive, used to judge whether a restock will arrive in time — but only if the vendor has no open unpaid invoice (see Business rules). |

## leases

| Field | Why it matters |
|---|---|
| id | Joins to `tickets.lease_id` for rent-related tickets. |
| space_name | Identifies which physical location the lease covers, for Facilities. |
| landlord | Who Facilities/Accounting would be paying. |
| monthly_rent | The amount Accounting must check against `cash_accounts.balance` before approving a rent payment. |
| next_due | Compared against `desk.date_today` to tell Facilities/Accounting whether rent is overdue or coming due. |
| notes | Freeform context for Facilities; not used in automated logic. |

## cash_accounts

| Field | Why it matters |
|---|---|
| name | Identifies the account (only one exists today: "checking"); referenced by `payments.account`. |
| balance | The hard ceiling Accounting's pay tool must check — no payment may push this negative. |
| date | When the balance was last known to be accurate; useful for Accounting to judge how fresh the number is. |

## payments

| Field | Why it matters |
|---|---|
| id | Unique record of a completed payment. |
| kind | Distinguishes what was paid (e.g. invoice vs. rent), so Accounting applies the payment to the right table. |
| ref_id | Points back to the specific `invoices.id` or `leases.id` being paid. |
| amount | What left the cash account; must reconcile against `cash_accounts.balance`. |
| account | Which `cash_accounts.name` the money came from. |
| paid_at | Timestamp for the audit trail. |
| approved_by | Records which human approved the payment — every payment requires human approval, so this field should never be blank. |

## invoices

| Field | Why it matters |
|---|---|
| id | Joins to `tickets.invoice_id` and `payments.ref_id`. |
| vendor_id | Joins to `vendors.id` — this is the only way to know which vendor a ticket's invoice belongs to. |
| amount | What Accounting must have cash on hand to pay, and what a payment record should match. |
| due_date | Compared against `desk.date_today` to flag an invoice as overdue. |
| status | Whether the invoice is "open" (unpaid) or paid — an open invoice blocks that vendor from shipping anything. |
| description | Human-readable context for what the invoice is for; helps confirm it matches the related ticket. |

## tickets

| Field | Why it matters |
|---|---|
| id | Unique identifier the Boss uses to track and route work. |
| type | Tells the Boss which agent should own the ticket (customer_order → Inventory/Customer Service, rent_notice → Facilities/Accounting, price_override → Boss/Accounting). |
| requester | Who asked for this — a customer, a landlord, a student org — shapes how Customer Service should respond. |
| subject | Short human summary of the ask. |
| sku | Joins to `inventory.sku` / `pricing.sku` for product-related tickets; null for tickets that aren't about a product (e.g. rent). |
| size | Needed alongside sku because inventory is tracked per size. |
| qty | What Inventory checks against `inventory.qty` to see if there's enough stock. |
| lease_id | Joins to `leases.id` for rent-related tickets. |
| invoice_id | Joins to `invoices.id` when the ticket is tied to an outstanding bill. |
| status | Whether the Boss still needs to act on this ticket ("open" for all three current tickets). |
| notes | Freeform detail from the requester, useful context for whichever agent picks this up. |
| created_at | Timestamp used alongside `desk.date_today` to judge how old/urgent a ticket is. |

---

## How the three open tickets link across tables

All values below are pulled directly from `data/campus_customs.db`. `desk.date_today` = **2026-08-31**.

### Ticket 101 — customer_order, "Bulldog tee" (Tauhid Zaman)
- **Product**: sku `CC-TEE-WHITE`, size `S`, qty 1.
- **Inventory**: `inventory` has `CC-TEE-WHITE` / size `S` at **qty 0** — there is no stock to fill this order; it needs a restock.
- **Pricing**: `unit_cost` $8.00, `list_price` $28.00 (from `pricing` where sku = `CC-TEE-WHITE`).
- **Invoice**: `invoice_id` 501 → `invoices` row: vendor_id 1, amount $840.00, due_date 2026-08-28, status **open**, description "Rush reprint CC-TEE-WHITE S" — this invoice's description matches the ticket's exact sku/size, so it's clearly the reprint order meant to cover this shortfall.
- **Vendor**: invoice.vendor_id 1 → `vendors` id 1, **Bulldog Print Co**, specialty "apparel reprint" (matches a tee reprint), `lead_days` 5.
- **Overdue check**: invoice due_date 2026-08-28 is **before** `desk.date_today` 2026-08-31 — the invoice is **3 days overdue**.
- **Vendor shipping rule**: because invoice 501 is open/unpaid, Bulldog Print Co **cannot ship** anything — including this reprint — until it's paid. The ticket is effectively stuck behind an unpaid bill.
- **Cash**: `cash_accounts` balance is $3,400.00 — enough to cover the $840.00 invoice on its own, but see the combined cash check below.
- **Lease**: `lease_id` is null — correctly, this ticket has nothing to do with the lease.

### Ticket 102 — rent_notice, "Rent due" (Elm City Properties)
- **Lease**: `lease_id` 1 → `leases` id 1, "Chapel Street shop", landlord Elm City Properties, `monthly_rent` $2,400.00, `next_due` 2026-09-02.
- **Overdue check**: next_due 2026-09-02 is **after** `desk.date_today` 2026-08-31 — rent is **not yet overdue**, it's due in 2 days.
- **Product/invoice fields**: sku, size, qty, and invoice_id are all null — correct, since this ticket is purely about the lease, not a product or an invoice.
- **Cash**: $2,400.00 against a $3,400.00 balance is affordable by itself, but **not** at the same time as the $840.00 invoice above — $2,400 + $840 = $3,240, leaving only $160.00 of the $3,400.00 balance if both were paid. Accounting/the Boss should treat these two tickets as competing for the same cash, with the overdue invoice (101) arguably taking priority since it's already late while rent is not.

### Ticket 103 — price_override, "Bulk hoodie discount" (Yale AI Club)
- **Product**: sku `CC-HOOD-NAVY`, size `M`, qty 20.
- **Inventory**: `inventory` has `CC-HOOD-NAVY` / size `M` at **qty 8** — only 8 of the 20 requested are in stock, a shortfall of 12.
- **Pricing**: `unit_cost` $22.00, `list_price` $58.00 — any discount the Boss/Accounting approves should be weighed against this margin.
- **Vendor for restock**: no vendor is linked on this ticket (no invoice_id), but the sku's specialty match would be **Bulldog Print Co** (apparel reprint, `lead_days` 5) if the shortfall needs to be filled.
- **Invoice**: none (`invoice_id` is null) — there's no outstanding bill tied to this ticket, so there's no vendor-shipping block here, only a potential future one if a restock order is placed.
- **Lease**: null — correctly unrelated to the lease.

### Things that look odd or are missing
- **No direct ticket → vendor link.** Tickets only reach a vendor indirectly, through `invoice_id` → `invoices.vendor_id`. A ticket that needs a restock but has no invoice yet (like ticket 103) has no way to record which vendor would fulfill it — that match has to be inferred from `vendors.specialty` rather than read from a foreign key.
- **Ticket 103 needs 20 units but only 8 are in stock, and nothing in the database captures that a restock/vendor order should be opened for it** — unlike ticket 101, there's no invoice yet reflecting the missing 12 hoodies.
- **`payments` is empty.** There's no historical record showing invoice 501 was ever paid or attempted, which fits with its "open" status but means there's no payment trail to cross-check against.
- Invoice 501's `due_date` (2026-08-28) is earlier than ticket 101's `created_at` (2026-08-31) — the invoice was already overdue before the customer ticket was even logged, which is worth flagging to a human rather than assuming it's fine.

---

## Confirmation: working copy

- `data/campus_customs_new.db` exists and its contents are byte-identical to `data/campus_customs.db` (same MD5 checksum), so it's a true, untouched copy of the original.
- `data/campus_customs.db` was not modified during this check (read-only connection used).

---

## MCP tools

Three read-only tools in `mcp_server/server.py`, built directly from what tickets 101, 102, and 103 depend on.

| Tool | Table(s) read | Unlocks ticket | Why this tool fits that ticket |
|---|---|---|---|
| `check_stock` | `inventory`, `pricing` | 101, 103 | Both tickets name a sku + size and a requested qty (101: tee S qty 1; 103: hoodie M qty 20) — this is the only way to see current qty/location and cost/price, and whether the request exceeds what's on hand. |
| `check_vendor_status` | `vendors`, `invoices` | 101 | Ticket 101's shortfall needs a restock, and its linked invoice (501, vendor_id 1) is open — this tool is the only way to confirm that an open invoice blocks that vendor (Bulldog Print Co) from shipping. |
| `check_lease_and_cash` | `leases`, `cash_accounts`, `desk` | 102 | Ticket 102 is purely about a lease — this tool is the only one that reads `leases`/`cash_accounts` and uses `desk.date_today` to say whether rent is overdue, due today, or upcoming, and whether cash covers it. |

**Overlaps and gaps found:**
- No ticket is covered by two tools — each of the three tools maps to a distinct concern (stock, vendor/invoice, lease/cash).
- **Ticket 103 has no tool that reaches a vendor or invoice**, even though its qty (20) exceeds stock (8) by 12. `check_vendor_status` could be used manually against Bulldog Print Co (apparel reprint) since there's no vendor_id on the ticket itself, but nothing in these three tools proposes or confirms a restock order for it — that's a gap for the Boss to close by hand for now, and matches the gap already flagged above ("ticket 103 needs 20 units... nothing in the database captures a restock order").
- Ticket 101 is the only one touched by two tables outside its own tool chain (`check_stock` for the shortfall, `check_vendor_status` for the blocking invoice) — both are needed together to fully resolve it.

## Planned later tools

- **list_open_tickets / get_ticket** — the Boss needs a way to see all open tickets (or pull one by id) before it can decide who should work on each one; right now there's no tool that reads `tickets` at all.
- **update_ticket_status** — once an agent acts on a ticket, its `status` needs to move off "open" so the Boss doesn't keep re-routing work that's already been handled.
- **pay_invoice / pay_rent** — payments require human approval and must refuse if `cash_accounts.balance` can't cover the amount; this is the only way any of the three tickets actually gets unblocked (e.g. ticket 101's vendor can't ship until invoice 501 is paid).
- **draft_customer_message** — Customer Service needs to produce a response (e.g. telling Tauhid Zaman about the tee S shortfall) without ever actually emailing a real customer; drafts stay on the board per the standing rules.
- **draft_purchase_order** — Inventory/Boss need a way to propose restocking a shortfall (like ticket 103's missing 12 hoodies) with a vendor and lead time, without that draft becoming a real order or invoice on its own.

---

## The 5-agent team

| Agent | Role | MCP tools it can call | Can delegate to |
|---|---|---|---|
| Boss | Reads tickets, routes work, makes the final call | `get_ticket`, `list_open_tickets`, `update_ticket_status` | Inventory, Accounting, Facilities, Customer Service |
| Inventory | Checks stock/shortfalls, proposes restocks | `check_stock`, `check_vendor_status`, `get_invoice`, `draft_purchase_order`, `update_ticket_status` | Boss, Accounting, Facilities, Customer Service |
| Accounting | Watches cash/invoices, requests payment approvals | `get_invoice`, `check_vendor_status`, `check_stock`, `check_lease_and_cash`, `get_cash_balance`, `request_payment`, `update_ticket_status` | Boss, Inventory, Facilities, Customer Service |
| Facilities | Handles leases/rent | `check_lease_and_cash`, `update_ticket_status` (payments only via delegation to Accounting) | Boss, Inventory, Accounting, Customer Service |
| Customer Service | Drafts customer messages, never sends | `get_ticket`, `draft_customer_message`, `check_stock`, `check_vendor_status`, `update_ticket_status` | Boss, Inventory, Accounting, Facilities |

Every agent can delegate to every other agent (full connectivity), but never to itself, and the delegation guard in `backend/delegation.py` blocks delegating back to an agent already on the current ticket's chain.

## MCP tools (13 total: 8 read, 5 write)

| Tool | Read/Write | Table(s) touched |
|---|---|---|
| `check_stock` | read | `inventory`, `pricing` |
| `check_vendor_status` | read | `vendors`, `invoices` |
| `check_lease_and_cash` | read | `leases`, `cash_accounts`, `desk` |
| `list_open_tickets` | read | `tickets` |
| `get_ticket` | read | `tickets` |
| `get_invoice` | read | `invoices`, `vendors` |
| `list_pending_approvals` | read | `pending_approvals` (Problem 7, backs `GET /approvals`) |
| `get_cash_balance` | read | `cash_accounts` (Problem 7, backs `GET /cash`; also added to Accounting's toolset in Problem 9 so it can check cash on non-lease tickets) |
| `update_ticket_status` | write | `tickets` |
| `draft_purchase_order` | write | `drafts` |
| `draft_customer_message` | write | `drafts` |
| `request_payment` | write | `pending_approvals` (reads `cash_accounts`) |
| `execute_approved_payment` | write | `payments`, `cash_accounts`, `invoices`, `pending_approvals` — not attached to any agent; only `backend/main.py`'s `/approvals/{id}/approve` route calls it directly |

`drafts` and `pending_approvals` are created with `CREATE TABLE IF NOT EXISTS` when the MCP server process starts (`mcp_server/server.py`'s `_init_tables()`), not on every database reset — see the Problem 9 fixes log below for a bug this caused.

## Audit trail (`output/audit_trail.json`)

Append-only JSON array written by `backend/audit.append_audit_entry`. Every entry has `timestamp`, `ticket_id`, `agent`, `step_type`, `tool_name`, `args_summary`, `result_summary`, `usage`, `stop_reason`. `step_type` values actually used in the code:

| step_type | Written by | Meaning |
|---|---|---|
| `delegation` | `backend/delegation.py`'s `delegate()` | One agent dispatching a sub-task to another; logged both at dispatch and (as the target's own `final_result`) on return, or as a refusal string if the depth/loop guard fired. |
| `final_result` | `delegate()` (for a delegated agent) and `backend/main.py`'s background run task (for the top-level Boss, added in Problem 9) | An agent's structured output once its own run finishes. |
| `tool_call` | `AuditedToolset` in `backend/mcp_toolset.py` (added in Problem 9) | Every individual MCP tool call any agent makes — real tool name, arguments, and result/error. Closes the gap where a malformed/failed call (e.g. the `request_payment` crash on ticket 101) left no trace of what was actually sent. |
| `payment_refused` / `payment_executed` | `backend/main.py`'s `/approvals/{id}/approve` route | The only route that calls `execute_approved_payment`; logs the outcome either way. |
| `reset` | `backend/main.py`'s `/reset` route | Confirms `scripts/reset_db.py` ran; never clears the file itself. |

## Safety

- **Human approval required before any payment executes.** `request_payment` only ever creates a `pending_approvals` row (status `pending`); no agent, and no code path reachable from an agent, can move money. Only `execute_approved_payment` moves money, and it isn't wired into any agent's toolset.
- **No negative balances, enforced twice.** `request_payment` checks `cash_accounts.balance >= amount` before creating the approval; `execute_approved_payment` re-checks the balance at execution time (in case other payments landed in between) inside the same transaction that would otherwise pay out.
- **Drafts only.** `draft_purchase_order` and `draft_customer_message` only ever write to the `drafts` table — no vendor is contacted, no customer is emailed.
- **Least-privilege tool assignment.** Boss has no stock/cash/lease tools — it can only read/route tickets, because it should always delegate specialist work. Facilities lacks `request_payment` — it must delegate rent payments to Accounting rather than requesting them itself. Customer Service lacks `request_payment`/`draft_purchase_order`/`check_lease_and_cash` — it only drafts messages. Inventory and Accounting lack `check_lease_and_cash`/`draft_customer_message` respectively — each agent only gets the tools its own prompt's "Tools you use" section lists. No agent anywhere has `execute_approved_payment`.
- **No secrets in audit logs.** `backend/audit.py` redacts any summary containing `api_key`, `password`, `secret`, `token`, or `portkey` (case-insensitive) to `[redacted]` before writing.
- **Append-only audit trail.** `append_audit_entry` does a lock-protected read-modify-write of `output/audit_trail.json` and writes via an atomic rename, so concurrent agent runs can't interleave-corrupt it and no entry is ever overwritten.

## Routes (`backend/main.py`)

CORS origin: `http://localhost:5173` only (Vite's default dev-server port for the React dashboard built in the next problem), with `allow_credentials=True` and explicit `allow_methods`/`allow_headers` wildcards — safe to combine credentials with wildcards here because the origin list is an explicit string, not `"*"`.

| Method | Path | What it does / underlying MCP tool or agent |
|---|---|---|
| GET | `/tickets` | Returns tickets 101-103 with their current `status`, each via `get_ticket` (MCP). |
| POST | `/tickets/{ticket_id}/run` | Checks the ticket exists via `get_ticket` (MCP) first (404 if not, before touching any agent), then **returns immediately with HTTP 202** `{"ticket_id", "status": "running"}` and kicks off the Boss agent run (`registry.get_agent("boss")` with a fresh `TicketContext`) as a background `asyncio.create_task`. A module-level `_RUN_STATE` dict tracks in-flight runs by `ticket_id`; a second `/run` call while one is already running returns the same `{"status": "running"}` shape instead of starting a duplicate. Completion is already visible via the agent's own `delegation`/`final_result` audit entries (no extra "done" marker needed) plus `GET /tickets` once `update_ticket_status` flips the ticket off `"open"`. |
| GET | `/tickets/{ticket_id}/run-status` | Added only to surface a case `/events` + `/tickets` can't: a background run crashing with an uncaught exception before writing any `final_result`. Returns `{"ticket_id", "status": "idle"|"running"|"done"|"error", ...}` from the in-process `_RUN_STATE` dict (`"idle"` if `/run` was never called for that ticket this process lifetime; `"error"` includes the exception string). Not persisted — resets on backend restart. |
| GET | `/events?limit=N` | Reads `output/audit_trail.json` directly (the backend's own file, not a second tool layer), returns the most recent `limit` entries, newest first. Returns an empty list if the file doesn't exist yet. |
| GET | `/approvals` | Lists pending payment approvals via the new `list_pending_approvals` MCP tool (`pending_approvals` where `status='pending'`). |
| POST | `/approvals/{approval_id}/approve` | The only route allowed to call `execute_approved_payment` (direct MCP call via `campus_customs_toolset.direct_call_tool`, no agent involved). On refusal, returns the tool's own reason as a 4xx and writes an audit entry (`step_type="payment_refused"`); on success writes `step_type="payment_executed"` with `agent_name="human"`. |
| GET | `/cash` | Returns the checking balance via the new `get_cash_balance` MCP tool. |
| POST | `/reset` | Runs `scripts/reset_db.py` via subprocess, then appends a `step_type="reset"` audit entry (`agent_name="system"`). Never clears `audit_trail.json` itself. |

New MCP tools added to `mcp_server/server.py` (both read-only, same style as the existing tools):
- `list_pending_approvals()` — needed because no existing tool exposed `pending_approvals` rows to the backend without raw SQL in `main.py`.
- `get_cash_balance(account="checking")` — chosen over piggybacking on `check_lease_and_cash` (which needs an arbitrary valid `lease_id` purely as a pretext and would be a misleading "it's about the lease" read for a route that's purely about cash).

MCP connection lifecycle: `backend/main.py` uses a FastAPI `lifespan` that holds `campus_customs_toolset` open (`async with campus_customs_toolset:`) for the life of the process. `MCPToolset.__aenter__`/`__aexit__` are reference-counted in the installed `pydantic_ai.mcp`, so each agent run's own `async with` over the same shared toolset instance, and each direct `campus_customs_toolset.direct_call_tool(...)` call (which also enters/exits the toolset), just increments/decrements that count rather than opening a second stdio subprocess — one persistent connection is reused everywhere.

No raw SQL appears in `backend/main.py` — every shop-fact read/write goes through an MCP tool call. No agent in `backend/agents/*.py` has `execute_approved_payment` in its toolset; it is only ever invoked directly from the `/approvals/{id}/approve` route.

### Token / runaway-cost limits

- **Delegation depth cap.** `TicketContext.max_depth` (default 3) is checked in `backend/delegation.py` before any delegation call is dispatched; once hit, the delegation tool returns a refusal string instead of calling the target agent.
- **Shared `UsageLimits` per ticket.** A single `RunUsage()` object is created once per ticket and threaded as `deps.usage` into every agent run and every delegated run, so `usage_limits=` set on the outermost `Agent.run()` call caps total tokens/requests across the *whole* ticket resolution, not per agent.
- **No self-delegation or cycles.** `TicketContext.visited_agents` accumulates as delegation descends; the guard refuses to delegate to any agent already in that set, which also rules out delegating to itself.
- **Max-steps-per-agent:** not separately implemented as a hard cap beyond PydanticAI's own per-run request limit (part of `UsageLimits.request_limit`); the delegation depth cap plus the shared token budget were judged sufficient for this project's scope.

## Dashboard (`frontend/`)

React + Vite + TypeScript, plain CSS and `fetch` only (no UI library), started with `npm run dev` from `frontend/`, calling the backend at `http://localhost:8000`. "Trading-floor ticker board" layout — full design rationale, agent color/icon mapping, and known gaps are in `output/design.md`; this section is the short version for completeness:

- **Tickets** render as cards (id, type, subject, requester, status pill) with a Run/Retry/Resolved button. Only a literally `resolved` status disables the button — a `blocked` ticket stays re-runnable (fixed in Problem 9; it originally looked as permanently stuck as a true resolution).
- **Live wire feed** polls `GET /events` and renders each entry color/icon-coded by `agent`, oldest-first like a real ticker.
- **Run completion** is detected via `GET /tickets/{id}/run-status`, not by watching the ticket's own `status` field — a run can finish and legitimately leave a ticket `open` (e.g. rent not due yet), which the status field alone can't distinguish from "still running" (fixed in Problem 9).
- **Pending approvals** (`GET /approvals`) show a confirm step with amount, purpose, and balance before/after before calling `POST /approvals/{id}/approve`; a refusal shows the backend's exact reason text.
- **Cash balance** (`GET /cash`) is always visible top-right and refetched after any approval attempt.
- **Drafts**: customer-message drafts render fully (extracted from `CustomerServiceResult.draft_text`); purchase-order drafts show that one was created but not its line items, since `InventoryResult` only carries `draft_po_id` — the new `tool_call` audit entries (see above) now carry the full `draft_purchase_order` arguments as a workaround, though the frontend doesn't yet read from them.

## Problem 9 fixes (found from the first manual run over all three tickets)

- **Accounting couldn't check cash on non-lease tickets.** Accounting's `ALLOWED_TOOLS` was fixed in Problem 5, before `get_cash_balance` existed (added in Problem 7); `check_lease_and_cash` requires a `lease_id`, which ticket 101 doesn't have, so Accounting had no legal way to verify cash before requesting payment on invoice 501 — and correctly refused to guess. Fixed by adding `get_cash_balance` to Accounting's toolset in `backend/agents/accounting.py`.
- **The board showed "Running…" forever for a ticket that had actually finished.** The Boss's run on ticket 102 completed in under a second each time (confirmed live via `GET /tickets/102/run-status` → `"status": "done"`), but Facilities correctly judged rent wasn't due yet and chose not to request payment, so Boss's own result legitimately left the ticket `status: "open"`. The frontend's `refreshTickets()` only cleared the "running" flag when a ticket's status moved off `"open"`, so a ticket that finishes but stays open never got marked done. Fixed by having the frontend poll `/tickets/{id}/run-status` and clear "running" on `"done"`/`"error"` regardless of the ticket's own status.
- **No audit entry existed for the Boss agent's own top-level completion** — only each delegated agent's `final_result` and the delegation dispatch events were logged (`backend/delegation.py`'s `delegate()` was the only call site). Fixed by having `backend/main.py`'s background run task append a `final_result` (or `error`) audit entry for `agent_name="boss"` once `boss_agent.run()` resolves, so the wire feed shows a definitive last word for every run.
- Ticket 103 (bulk hoodie discount) still correctly ends up `blocked`: there is no MCP tool or table representing a discount policy, so Inventory/Customer Service have no way to answer "is this discount allowed." This is a data/scope gap, not a bug, and was left as-is.
- **`request_payment` crashed the whole ticket-101 run with `UnexpectedModelBehavior: Tool 'request_payment' exceeded max retries count of 1`** on a later clean run. PydanticAI's MCP toolsets default to `max_retries=1`; a retry is consumed when a tool call's arguments fail schema validation, and a second malformed attempt exhausts the budget and raises. There was no record of the actual bad arguments, because individual MCP tool calls were never logged (only delegations and each agent's own `final_result` — see `backend/delegation.py`'s `delegate()`). Two fixes:
  - Raised `MCPToolset(..., max_retries=3)` in `backend/mcp_toolset.py` so a one-off malformed call gives the model a couple of chances to self-correct before the run gives up.
  - Added a new `"tool_call"` audit step type: `AuditedToolset` in `backend/mcp_toolset.py` is a `WrapperToolset` subclass that every agent's restricted toolset is now wrapped in (`restricted_toolset(tools, agent_name)` takes the calling agent's name), logging the exact tool name, arguments, and result (or error) for every individual MCP call. Verified live: a smoke-test `check_stock` call produced a `tool_call` entry with the real request/response JSON. This also closes the Problem 8 "purchase-order draft contents aren't visible" gap, since `draft_purchase_order`'s real arguments are now logged.
- **`/reset` doesn't recreate `drafts`/`pending_approvals`, because they're only created once at MCP-server-process startup (`_init_tables()`'s `CREATE TABLE IF NOT EXISTS`), not on every reset.** A reset run mid-session (while testing the fix above) dropped both tables from the live file while the backend's own long-running MCP subprocess kept running on its original connection, so every `request_payment` call afterward failed with `"no such table: pending_approvals"` until the backend process itself was restarted. No code fix was applied for this (a cleaner fix would be to also create these tables, or trigger an MCP-subprocess restart, from the `/reset` route itself) — it was worked around for this session by restarting the backend process, which is noted here as a real remaining gap.
- **A `blocked` ticket's Run button was indistinguishable from a resolved one** — `TicketBoard.tsx` disabled the button for any non-`open` status, so there was no way to retry a blocked ticket from the board at all. Fixed by only disabling for a literally `resolved` status; a `blocked` ticket now shows an enabled **Retry** button.
- **A retried ticket can short-circuit on its own stale notes.** `update_ticket_status` only ever appends to a ticket's `notes` field, never clears it. When ticket 101 was retried after the `pending_approvals` fix above, Boss read the ticket's own notes (which already said "payment approval request could not be created... no money moved" from the earlier failed run), concluded nothing had changed, and re-blocked the ticket without delegating to Inventory or Accounting at all this time (`agents_used: []`, zero tool calls beyond `get_ticket`/`update_ticket_status`). **No code fix was applied** — the user chose to document the ticket's actual final state (still blocked, invoice 501 still unpaid) rather than patch the notes or the prompt. A real fix would either have Boss's prompt explicitly disregard prior blocker notes and re-verify via tools every run, or have a way to clear/reset a ticket's notes independent of a full database reset.
- **Net result: no payment was ever actually approved anywhere in this exercise.** The only `execute_approved_payment` calls in the entire audit trail are old test calls against a fake approval id (99999) from the Problem 7 subagent's own smoke test, which were correctly refused. `payments` is empty, invoice 501 is still `open`, and the checking balance never moved from $3,400.00. See `output/resolved_tickets.json` and the Cash tab of `output/desk_tickets.html` for the full accounting of this.
