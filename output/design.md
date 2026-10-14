# Campus Customs — Dashboard Design Notes

## Backend change: async `/tickets/{id}/run`

The original route did `await boss_agent.run(...)` and only returned once the
whole delegation chain finished — unusable for a "live" dashboard, since the
HTTP request itself would hang for the duration of the run.

Changed in `backend/main.py`:
- `POST /tickets/{ticket_id}/run` still does the existing MCP `get_ticket`
  existence check first (404 for an unknown ticket, unchanged), but now
  returns **HTTP 202** immediately with `{"ticket_id", "status": "running"}`
  and starts the actual Boss-agent run via `asyncio.create_task(...)`.
- A module-level `_RUN_STATE: dict[int, dict]` tracks in-flight runs by
  `ticket_id`. A second `POST /run` on an already-running ticket returns the
  same `{"status": "running"}` shape (with a `detail` note) instead of
  starting a duplicate agent run.
- The background task doesn't need to write any special "done" marker: the
  Boss/delegate calls already write `delegation` and `final_result` audit
  entries through `backend.audit.append_audit_entry` as they happen, and
  `update_ticket_status` flips the ticket's `status` off `"open"` once the
  Boss acts — both are exactly what the frontend polls.
- I added one new route, `GET /tickets/{id}/run-status`, specifically to
  cover the one thing `/events` + `/tickets` genuinely can't show: a
  background run that crashes with an uncaught exception before it ever
  gets to write a `final_result`. `_run_ticket_background` wraps the run in
  try/except; on failure it records `{"status": "error", "error": str(exc)}`
  in `_RUN_STATE` *and* writes an audit entry (`step_type="final_result"`,
  `agent_name="system"`) so the crash is visible in both places. This state
  is in-memory only (resets on backend restart) — acceptable since it's a
  diagnostic aid, not the system of record (the audit trail is).
- No new logging mechanism was introduced; everything still goes through
  `append_audit_entry`.

`output/harness.md`'s Routes table was updated to describe both changes.

## Is there already a per-ticket "what did this agent do" summary?

Yes, two usable sources, and I used both:
- `BossResult` (`backend/models.py`, same fields as `TicketDecision`) has
  `agents_used`, `key_facts`, `actions_taken`, `next_steps` — exactly the
  shape of an end-of-run summary. Since `/run` no longer resolves directly to
  this value (it returns 202), the frontend recovers an equivalent summary
  by reading the Boss's own `final_result` audit entry for that ticket
  (`TicketBoard.tsx`'s `buildFallbackSummary`), plus the union of agents that
  produced `final_result` entries on that ticket, as a stand-in for the
  full `BossResult.agents_used`/`key_facts`/`actions_taken` (which aren't
  separately reconstructable from the stringified `result_summary` alone —
  see gaps below).
- A live "what did agent X do" view is also available for free, by filtering
  `/events` client-side by `agent` and `ticket_id` — that's what the Wire
  feed does.

## Frontend layout: "trading-floor ticker board"

`frontend/` — Vite + React + TS, plain CSS, fetch only, no UI libraries.

```
frontend/
  src/
    main.tsx
    App.tsx                  # layout + polling orchestration
    App.css                  # all component styling (Yale navy/gold theme)
    index.css                # CSS variables + resets
    types.ts                 # TS mirrors of backend/models.py response shapes
    api.ts                   # fetch wrappers, base URL http://localhost:8000
    agentMeta.ts              # agent -> {label, icon, color} mapping
    components/
      TicketBoard.tsx        # ticket grid + run button + end-of-run summary
      WireFeed.tsx            # scrolling ticker of audit events
      ApprovalsPanel.tsx      # pending approvals + confirm-then-approve flow
      DraftsPanel.tsx         # customer-message / PO drafts, "never sent"
```

- **Header**: dark navy→gold gradient bar, big cash balance top-right
  (`GET /cash` on load and refetched after every approved payment and on
  every poll tick), plus a manual "Refresh" button.
- **Ticket grid**: one card per ticket (101/102/103) — id, type, subject,
  requester, a status pill (red/open vs. green/resolved). The "Run" button
  disables itself and reads "Running…" the instant `POST /run` is accepted,
  and re-enables (reading "Resolved") once `GET /tickets` shows `status`
  off `"open"`.
- **Wire feed**: fixed-height scrollable panel at the bottom styled like a
  terminal/ticker (monospace, dark background, one line per audit event),
  polled from `GET /events` every 1.5s while any ticket is running and every
  6s otherwise. Events are reversed client-side so the feed reads
  chronologically top-to-bottom like a real ticker (the backend returns
  newest-first).
- **Approvals** and **Drafts** sit side-by-side below the ticket grid.

## Agent color / icon mapping (`src/agentMeta.ts`)

| Agent | Icon | Color | Why |
|---|---|---|---|
| boss | 👑 crown | gold (`#e6c66b`) | Decision-maker, matches the gold accent already used for emphasis everywhere else. |
| inventory | 📦 box | cyan-blue (`#5bc0de`) | Boxes/stock. |
| accounting | 💰 money bag | green (`#4caf50`) | Money, distinct from gold (used for the Boss) and from red (used for "open"/error states). |
| facilities | 🏢 building | orange (`#ff8a3d`) | Buildings/leases, a warm color distinct from the other four. |
| customer_service | 💬 speech bubble | purple/violet (`#c77dff`) | Communication-flavored purple, distinct from the navy used for the base theme. |
| human (approvals) | 🧑 person | off-white | Neutral, since approval actions are the human's own. |
| system (reset / crash marker) | ⚙ gear | muted gray | Background/infrastructure events, deliberately de-emphasized. |

Each wire-feed row is colored by this mapping on the agent tag so you can
tell at a glance who's talking without reading the text.

## Resolved tickets & cash balance

- Resolution is detected purely by polling `GET /tickets` and watching
  `status` move off `"open"` — no page reload needed. When that happens the
  card gets the green "resolved" border/pill and an "End-of-run summary"
  block appears underneath (see above for where that summary comes from).
- Cash balance is a big always-visible number in the header, refetched after
  any `POST /approvals/{id}/approve` call succeeds and on every poll tick, so
  it reflects reality without a reload.

## Approval confirmation flow

`ApprovalsPanel.tsx`: each pending approval card shows amount, a
human-readable purpose (`"Invoice #501"` / `"Lease #1 rent"`, derived from
`kind`/`ref_id` — `kind === "invoice"` → `Invoice #{ref_id}`, `kind` of
`"rent"`/`"lease"` → `Lease #{ref_id} rent`, otherwise a generic
`"{kind} #{ref_id}"` fallback), and the account. Clicking "Approve" doesn't
call the backend yet — it opens a confirmation box showing: payee/purpose,
amount, current balance (from the `cash` state already in `App.tsx`), and
"balance if approved" computed client-side as `balance - amount` and
labeled accordingly. Only "Confirm payment" in that box calls
`POST /approvals/{id}/approve`. If the backend responds 4xx, `api.ts`'s
`handle()` reads the JSON body's `detail` field and throws it as the error
message verbatim, and `ApprovalsPanel` renders that exact string in a
visible error line under the card (not a generic "something went wrong").

## Drafts: what's actually shown, and the gap

There is no `GET /drafts` route, and I didn't invent one. What's reachable
through the existing audit trail:

- **Customer-service drafts: fully shown.** `CustomerServiceResult` (in
  `backend/models.py`) has a `draft_text` field, and `backend/delegation.py`
  writes the stringified agent output (`str(result.output)`) into the
  `result_summary` of a `final_result` audit entry whenever `customer_service`
  finishes. `DraftsPanel.tsx` regex-extracts `draft_text='...'` out of that
  string and renders it in a dashed-border, "DRAFT — never sent" badge card.
  This is the best available signal short of a dedicated route, and it works
  because `CustomerServiceResult` happens to carry the full draft text in its
  structured output.
- **Purchase-order drafts: was only partially shown — now fixed (Problem 9).**
  `InventoryResult` only ever carried `draft_po_id` (an integer), never the
  drafted PO's actual line-item text, because no `tool_call` audit entries
  existed anywhere — `backend/delegation.py` only logged `"delegation"` and
  `"final_result"`. This was closed in Problem 9 by wrapping every agent's
  MCP toolset in a `WrapperToolset` subclass (`AuditedToolset` in
  `backend/mcp_toolset.py`) that logs a `"tool_call"` audit entry — full
  arguments and result — around every individual MCP call, keyed by the
  calling agent's name. So when Inventory creates a PO draft, the raw
  `draft_purchase_order` arguments (sku, size, qty, vendor, cost) now land in
  `output/audit_trail.json` directly; `DraftsPanel.tsx` can be updated to read
  from these `tool_call` entries instead of regex-scraping `final_result`
  strings, which is a more reliable source going forward. (This also was the
  fix that let the exact cause of the `request_payment` retry-exhaustion
  crash on ticket 101 be diagnosed, rather than guessed at.)

I did not fabricate a drafts API or invent new backend fields to "fix" this
— the gap is called out here and in the relevant component's code comment
instead.

## Visual theme choice

Reused the exact Yale navy/gold CSS variables from `output/desk_tickets.html`
(`--black`, `--purple` as the navy accent, `--purple-light`, `--gold`,
`--gold-light`, `--panel`, `--text`, `--muted`) rather than inventing a new
palette, per the instruction to keep visual consistency across the project
unless there's a clear reason not to. There wasn't one — the ticker-board
concept (dark background, bright accent highlights, monospace feed) maps
naturally onto the same navy/gold language already established for this
project's other HTML page.

## Testing notes

- Backend started with `uvicorn main:app --port 8000` from `backend/`
  (without `--reload`, since this was a one-shot smoke test, not active
  development) — came up cleanly, MCP stdio subprocess ("Campus Customs"
  FastMCP server) started as part of app startup.
- Verified via `curl`: `GET /tickets` (real ticket data for 101/102/103),
  `GET /cash` (`{"account":"checking","balance":3400.0,...}`), `GET /approvals`
  (empty, as expected pre-run), `GET /tickets/101/run-status` (`{"status":"idle"}`).
- Verified CORS explicitly: `curl -H "Origin: http://localhost:5173" .../tickets`
  returned `access-control-allow-origin: http://localhost:5173` and
  `access-control-allow-credentials: true` — matches the frontend's exact
  origin (protocol, host, port).
- Frontend started with `npm run dev` from `frontend/` — Vite served on
  `:5173`. `npx tsc -b` passed with zero errors (strict `noUnusedLocals`/
  `noUnusedParameters` included). Every source module (`App.tsx` and all of
  `components/*.tsx`, `api.ts`, `types.ts`, `agentMeta.ts`) was requested
  directly through Vite's dev server and returned HTTP 200 with valid
  transformed JS (a compile error in any of these would have produced a
  500 with an overlay error instead) — this was my substitute check for a
  live browser console, since **no interactive browser/screenshot tool was
  available in this task's environment**; I did not fabricate a screenshot.
- Did not run a full ticket end-to-end, per the instruction that the user
  wants to do that themselves.
- Both dev servers were stopped after testing, and `scripts/reset_db.py` was
  run once more at the end regardless, per instructions.

## Deviations from spec

- No `GET /drafts` route was added (by design — see Drafts section above);
  flagged as a gap instead of inventing one.
- `output/design.md` (this file) and the `/tickets/{id}/run-status` route
  were both judged necessary/useful per the spec's own conditional language
  ("ONLY if...", "only if you judge...") rather than being default
  additions.
- Could not capture an actual browser screenshot or live console-error
  check — no browser automation tool was available in this subagent's
  environment. Verification instead relied on `curl` against both servers,
  explicit CORS header inspection, a clean `tsc -b`, and confirming every
  frontend module transforms successfully through Vite's dev server.
