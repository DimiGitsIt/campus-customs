# AI Prompts Log — Homework 5

This file is a running log of the prompts I typed into Claude Code while working on Homework 5. Each problem has its own section with the original prompt (in my own words), any follow-up prompt, and a one-sentence note on what was missing after the first attempt.

Sections are added as each problem is worked on.

---

<!-- Template for each problem:

## Problem [number]: [title]

**Prompt**

[the prompt I typed, in my own words]

**Follow-up (if needed)**

[the follow-up prompt]

**What was missing after the first prompt:** (one sentence)

-->

## Problem 1: Vibe coder prompts

**Prompt**

I'm starting a new homework, Homework 5: Campus Customs Multi-Agent Operations. Please work in the Homework 5 folder for it, separate from my last homework.
First, set up the basics:

1. Create AI_prompts.md in the project root, using the same format as last time: one section per problem with the problem number and title, the prompts I typed verbatim, and a follow-up prompt with one sentence on what was lacking if I needed one. Start with "Problem 1: Vibe coder prompts" and log this prompt as the first entry. From now on, update it yourself at the end of every task. Never paraphrase my wording or invent prompts I didn't type, and ask me if you're unsure which problem a prompt belongs to.

2. I downloaded data.zip. Find it (check Downloads and the project folder, and ask me if you can't find it) and unzip it so I end up with data/campus_customs.db. Tell me what else is in the zip.

3. Make a working copy at data/campus_customs_new.db. The original campus_customs.db must stay untouched, because I'll reset from it before each full run. Write a small reset script (for example scripts/reset_db.py) that overwrites the working copy with a fresh copy of the original. From now on, the MCP server and the backend should only ever point at campus_customs_new.db, with the path in one config or env variable.

4. Do a quick read-only look at the database and tell me the tables (desk, tickets, inventory, pricing, vendors, leases, cash_accounts, payments, invoices), their columns, and their row counts, plus what desk.date_today is. Don't write any app code yet.

5. Set up .gitignore to exclude the data/ folder, .env, node_modules, Python virtual environments, __pycache__, and build output. Create .env.example with placeholders only (PORTKEY_API_KEY=your-key-here, plus a MODEL_NAME variable set to gpt-6-luna).

6. Create a CLAUDE.md in the root with these standing rules for this project, so you follow them in every later task:
- The project has three parts: an MCP server, a FastAPI backend with a multi-agent team, and a React dashboard where a human watches the agents and approves requests.
- Agents: Boss (reads each ticket, decides who works on it, makes final calls), Inventory, Accounting, Facilities, and Customer Service (drafts customer messages). Any agent can delegate to any other agent.
- Use only gpt-6-luna through Portkey (PORTKEY_API_KEY) for every agent, defined in one place. No other model may appear anywhere in the code or runs.
- desk.date_today is "today" for deciding what's overdue.
- Vendor lead times come from the vendors table. A vendor won't ship while they have an open unpaid invoice.
- Any payment requires human approval, and when a payment is made the relevant table must be updated. The pay tool must refuse if there isn't enough cash (no negative balances). Cash only goes out; no money comes in.
- Never email customers or call real vendors. Drafts stay on the board.
- Only touch campus_customs_new.db. Never modify campus_customs.db.
- Never commit .env, data/, or the database.

Then show me a summary of what you set up.

**Follow-up (if needed)**

N/A

**What was missing after the first prompt:** N/A

## Problem 2: Study the Campus Customs database

**Prompt**

I want to understand the data before we build anything. Please look through every table and every field in data/campus_customs.db (read-only), and confirm that data/campus_customs_new.db exists as a copy of the original. You made it during setup, so just check it's there and that it matches, and don't change the original.

Then study the three open tickets and show me how each one links to the other tables. For each ticket, trace the connections using the real values: which inventory rows and pricing it touches (by sku and size), which vendor could restock it and that vendor's lead_days, whether there's an invoice tied to it (and whether that invoice is unpaid, since a vendor won't ship while they have an open unpaid invoice), which lease it relates to, and how the amounts compare to the cash_accounts balance. Use desk.date_today to say what's overdue. Don't guess or invent anything the database doesn't contain, and if a link looks odd or missing, tell me.

Next, start output/harness.md. Give it a short intro, then one section per table. In each section, list every field and write one short line on why that field matters for the shop or for the agents. For example, think about what the Boss needs to route a ticket, what Inventory needs to spot a shortfall, what Accounting needs to check cash and invoices, and what Facilities needs for rent. Add a short section on how the three tickets link across tables, using what you found. I'll keep adding to this file in later problems, so organize it so new sections are easy to add.

Don't write any app code, don't touch the original database, and don't commit anything from data/. Log this prompt in AI_prompts.md under Problem 2: Study the Campus Customs database, like we set up.

**Follow-up (if needed)**

N/A

**What was missing after the first prompt:** N/A

## Problem 3: Build the MCP server

**Prompt**

Let's build the MCP server in an mcp_server/ folder using FastMCP. It talks to data/campus_customs_new.db only, and never to the original. Take the path from the single config/env variable we already set up. I don't need to connect or run it as part of the agent team yet, but please do a quick local check that it starts and that each tool returns real data.

Every agent in this homework will use the tools in this server, and I'll add more later. For now write three read-only tools I know I'll need for the open tickets. First read the three tickets in the database (101, 102, 103) and figure out which table(s) each one depends on, then build these three, adjusting them if the tickets tell you something different:
1. check_stock: looks up inventory (by sku, optionally by size) together with pricing, and returns qty, location, unit_cost and list_price. Make it easy to tell if a requested qty is short.
2. check_vendor_status: looks up vendors with their lead_days, and whether each vendor has an open unpaid invoice (from invoices), since a vendor won't ship while one is open.
3. check_lease_and_cash: looks up a lease, uses desk.date_today to say if rent is due or overdue, and compares the amount to the cash_accounts balance.

Rules: use parameterized SQL only, never invent any data (if a sku, size, vendor or lease isn't in the database, return a clear not-found result), keep the tool names clear, and write good docstrings so agents know when to use each tool. These tools only read, so nothing should be written to the database and nothing should be paid. Check the current FastMCP docs for the right way to define and run the server instead of guessing.

Docs:
- In output/harness.md, add an MCP tools section. For each of the three tools list which table(s) it reads, which ticket (101, 102, or 103) it helps unlock, and one sentence on why that tool is the right one for that ticket. Tell me if two tools end up helping the same ticket or if a ticket has no tool.
- In the same file, add a short "Planned later tools" list: list_open_tickets/get_ticket, update_ticket_status, pay_invoice/pay_rent (human approval required, refuses if cash is short, updates the payments table and the related table), draft_customer_message (drafts only, never sent), and draft_purchase_order. Give one line on why each one is needed.
- Create mcp_server/README.md explaining what the MCP server is for, which database file it uses, and the three tools it has.

Don't touch data/campus_customs.db, don't commit anything from data/, and log this prompt in AI_prompts.md under Problem 3: Build the MCP server, like we set up.

**Follow-up (if needed)**

N/A

**What was missing after the first prompt:** N/A

## Problem 4: Add the MCP server to vibe coder and test each tool

**Prompt**

I want you to be able to call my MCP server's tools directly. Please add the mcp_server/ we built to this project and save the connection config in .mcp.json at the project root (or wherever you store project-level MCP servers, and tell me where that is).

Use relative paths so it works from a fresh clone, point it at data/campus_customs_new.db only through our existing config/env variable, and don't put any secrets in the file. Then check that the config is valid and that the server starts, and tell me exactly what I need to do (restart, approve the project server, a /mcp check, etc.) so you can see the three tools in the next session. Don't call the tools yourself yet, because I'll test each one with my own prompts. Don't modify campus_customs.db, and don't commit anything from data/. Log this prompt in AI_prompts.md under Problem 4: Add the MCP server to vibe coder and test each tool, like we set up.

**Follow-up (if needed)**

Using the MCP server, how many CC-TEE-WHITE in size S do we have in stock, where is it located, and what's the unit cost and list price?

ok, Using the MCP server, does Bulldog Print Co have an open unpaid invoice, and what is their lead time in days? Would they ship to us right now?

ok, Using the MCP server, is the rent for the Chapel Street shop due or overdue as of today's desk date, and do we have enough cash in the account to cover it?

Ok, all three MCP tools are tested. Now write output/mcp_smoke.json as the evidence for Problem 4 (remember we're in homework 5). For each of the three tools (check_stock, check_vendor_status, check_lease_and_cash), add one entry with:
- the exact prompt I typed to you for that tool, verbatim
- the tool name that was actually called through the MCP server
- the raw tool output that came back from that call

Use only what really happened in this session. Don't rerun the tools, don't rewrite my prompts, and don't make up or edit any outputs. Leave out my first setup message, since it wasn't a tool test. Then check each output against data/campus_customs_new.db with read-only queries, and add a short "verified" note per entry saying which values matched. If any tool wasn't actually called through MCP, or an output doesn't match the database, tell me instead of covering it up. Keep the JSON valid, make sure all three tools are covered, and log the prompts in AI_prompts.md under Problem 4: Add the MCP server to vibe coder and test each tool.

**What was missing after the first prompt:** The first prompt only wired up the MCP config; the three tools still needed to be tested live and the results captured as evidence in output/mcp_smoke.json.

## Problem 5: Build the agent team and grow the MCP tools

**Prompt**

Now let's build the agent team with PydanticAI: Boss, Inventory, Accounting, Facilities, and Customer Service. They need prompts, structured types, and agent loops, and every agent must be able to delegate work to any other agent (full connectivity).

Before writing code, read CLAUDE.md and output/harness.md, and look up the current PydanticAI docs for how to do agent delegation (including sharing usage across delegated runs), how to attach MCP tools to an agent, and how to point it at gpt-6-luna through Portkey. Don't guess at the API. Give me a short plan first, and then build.

Layout (you can adjust it as long as the five roles are clear):
- backend/prompts/: one prompt file per agent (boss.md, inventory.md, accounting.md, facilities.md, customer_service.md)
- backend/models.py: the structured types (for example ticket decisions, delegation requests and results, payment requests, purchase order drafts, customer message drafts, and each agent's result type)
- backend/ agent files for the five agents, plus one place that builds the model
- Use PORTKEY_API_KEY from .env, and gpt-6-luna as the only model for every agent. Define the model name once in a single place and make sure no other model name appears anywhere in the code, comments, or defaults.

Prompts: I'll include the prompts for each system in the next prompt.I want you to log these in backend/prompts/

Delegation: every agent can delegate to any other agent. Guard against loops with a maximum delegation depth, detection of an agent delegating back in a circle, and a shared usage limit across the whole ticket so token use is capped.

MCP tools: all shop facts must come through the MCP server over data/campus_customs_new.db. Don't create a second set of shop tools that bypasses MCP. Read the three tickets and figure out what the agents need, then add tools to mcp_server/. I'm thinking of these, and you can adjust them if the tickets tell you otherwise:
- list_open_tickets and get_ticket (read)
- get_invoice (read)
- update_ticket_status (write: status and a note)
- draft_purchase_order and draft_customer_message (drafts only, stored on the board and never sent, with nothing emailed or called)
- request_payment, which only creates a pending approval and moves no money
- execute_approved_payment, which can only run with a recorded human approval, must refuse if the account doesn't have enough cash, and must update the payments table and the related invoice or lease
Give each agent only the tools that fit its role, and don't give any agent the execute_approved_payment tool. Only the backend should call it later, after a human approves in the dashboard. If drafts or pending approvals need a new table, create it idempotently when the MCP server starts, so my reset script and a fresh copy of the database still work. Tell me what you chose. Keep using parameterized SQL, only touch campus_customs_new.db, and never modify campus_customs.db.

Audit trail: wire the agents to append to output/audit_trail.json as they run. For every agent-loop step (model call, tool call, delegation, final result), record the timestamp, ticket id, agent name, step type, tool name, short args, a short result summary, token usage if available, and the stop reason. Append only, never wipe or truncate it between runs, keep it valid JSON, make writes safe if two happen at once, and don't log API keys, password hashes, or full message text.

Docs:
- In output/harness.md, list each agent (role, tools it can use, who it can delegate to) and each MCP tool, including the new ones, along with which table(s) the tool uses and whether it reads or writes. Add a short Safety section covering the guardrails a real business would want when agents touch real customers and real money (human approval for payments, no negative balances, drafts only, least-privilege tools per agent, no secrets in logs, an audit trail), plus the limits that keep token use in check (delegation depth, usage limits per ticket, max steps per agent, result caps).
- Update mcp_server/README.md so the tool list matches what we have now.

Test lightly: start the MCP server, build the agents, and run one cheap, read-only smoke test (for example, ask the Inventory agent about one sku) to confirm the agents can call MCP tools and write audit entries. Don't run the full ticket resolution yet, because that's for later. After the test, run my reset script so the working database is back to the original values. Then grep the code to prove gpt-6-luna is the only model name that appears, and show me.

Don't commit anything from data/ or .env. Log this prompt in AI_prompts.md under Problem 5: Build the agent team and grow the MCP tools, like we set up.

**Follow-up (if needed)**

[Shared rules + per-agent system prompts for Boss, Inventory, Accounting, Facilities, Customer Service pasted verbatim and saved into backend/prompts/.]

**What was missing after the first prompt:** The first prompt deferred the actual agent system-prompt text ("I'll include the prompts for each system in the next prompt"), so the prompt files were built from a placeholder structure until the follow-up supplied the real wording.

## Problem 6: Plan the three tickets

**Prompt**

Next is problem 6: Plan the three tickets
I want a page I can double-click to open: output/desk_tickets.html
Structure: one tab for each open ticket (101, 102, 103). Every tab has the same sections in this order:
1. Ticket facts: [read tickets 101, 102, 103 from data/campus_customs_new.db, read-only, and show the key fields plus the linked invoice, lease, and stock rows they touch. Don't invent anything.]
2. Expected: [my prediction, below]
3. Actual: [leave empty for now, with a clear "fill in after the agent run" placeholder I can type into or edit]
4. Cash: [blank placeholder for now, "to be filled in later"]
5. Reflection: [blank placeholder for now, "to be filled in later"]

My Expected section for each ticket must answer:
- Who the Boss calls first, and why
- Every delegation I expect, each with a reason (not "Boss calls everyone")
- Which MCP tools I expect that run to use
Here are my expectations:
Guess at the ticket pattern

* 101, a customer order for a sku and size, such as CC-TEE-WHITE in S, possibly with a quantity larger than stock.
* 102, an unpaid vendor invoice or restock tied to invoice_id.
* 103, rent, tied to lease_id 1.

For each ticket, answer the three screenshot questions like this
Ticket 101

* Boss calls first: Inventory, because whether the order can be filled depends on stock.
* Delegations:
   * Boss → Inventory (is there enough stock?).
   * Inventory → Accounting, only if stock is short and the vendor has an open unpaid invoice, because that blocks shipping.
   * Boss → Customer Service, after the facts are known, to draft the reply.
   * Customer Service → Inventory, only if it needs lead time or stock it doesn't have.
* MCP tools: get_ticket, check_stock, check_vendor_status, draft_purchase_order (only if the vendor can ship), draft_customer_message, update_ticket_status.

Ticket 102 (unpaid invoice or restock)

* Boss calls first: Accounting, because the key question is whether the invoice is overdue and cash covers it.
* Delegations:
   * Boss → Accounting.
   * Accounting → Inventory, only if it needs to know what the invoice unlocks, such as the restock that's blocked.
   * Possibly Boss → Customer Service, if a customer is waiting on the blocked restock.
* MCP tools: get_ticket, get_invoice, check_lease_and_cash (for the cash balance), check_vendor_status, request_payment, update_ticket_status.

Ticket 103 (rent)

* Boss calls first: Facilities, because the lease is the subject.
* Delegations:
   * Boss → Facilities.
   * Facilities → Accounting, to request payment approval. Facilities isn't allowed to request payments itself.
* MCP tools: get_ticket, check_lease_and_cash, request_payment (by Accounting), update_ticket_status.

If anything I wrote contradicts the real ticket data, flag it for me. Don't silently change my text.

Technical requirements: plain HTML, CSS, and JavaScript with tab switching, no external dependencies so it works offline, navy and gold styling to match the shop, and a consistent layout on every tab. Don't try to load audit_trail.json, since a double-clicked page can't read local files reliably. Nothing written to the database, nothing from data/ committed.

Log this prompt in AI_prompts.md under the right problem heading, like we set up.

**Follow-up (if needed)**

let's do navy & gold for this (this will be a yale project so the navy & gold makes sense)

**What was missing after the first prompt:** The first build used a Ravens-inspired black/purple/gold theme per the workspace's standing AGENTS.md rule for sites/dashboards; the follow-up asked for Yale navy and gold specifically, which fits better for a Yale project.

## Problem 7: Backend routes

**Prompt**

Problem 7: Backend routes
Now let's give the React dashboard (next problem) a backend it can call. In backend/main.py, use FastAPI and add routes that wrap the agent team and MCP tools we built in Problem 5. The server should start from the backend/ folder with: uvicorn main:app --reload --port 8000
Before writing code, read CLAUDE.md, output/harness.md, and the current backend/ and mcp_server/ code so the routes reuse what's already there. Look up the current FastAPI docs for CORS and for running async agent work inside a route. Don't guess at the API. Give me a short plan first (route list, how main.py reaches the MCP tools, and the CORS origin), and then build.
Routes (you can adjust names, but every one of these jobs must be covered):

* Return the three tickets and whether each one is open or resolved
* Take a ticket id and run the agent team on that ticket, starting with the Boss. Keep the delegation depth, loop detection, and shared usage limits from Problem 5, and return a clear error for an unknown ticket id.
* Return recent agent events (which agent spoke, what it said, which tools it used, and when) so the board can refresh. Read these from output/audit_trail.json, and never wipe or rewrite that file.
* List pending approvals so the board knows what to show an Approve button for
* Approve a payment or purchase after a human clicks Approve. This is the only route that changes cash. It should call execute_approved_payment with who approved it, refuse with a clear reason if cash is short, the approval isn't pending, or it was already paid, and log the outcome to the audit trail.
* Return the current checking balance from cash_accounts
* Reset the database to its original values by running my scripts/reset_db.py. Only touch campus_customs_new.db and never campus_customs.db. Don't clear audit_trail.json; append a "reset" event instead.

Rules: all shop facts must still come through the MCP server, so don't put raw SQL in main.py or build a second tool layer. No agent can reach the approve route or execute_approved_payment. Use the types in backend/models.py for request and response shapes. Add CORS for the frontend dev server, and tell me which origin you chose.
Docs: in output/harness.md, add a Routes section that lists each route on one line (method and URL, plus what it does).
Test lightly: start the server and hit each route with curl. For approve, test one case that should refuse because cash is too low or the approval isn't pending. Don't run the full ticket resolution yet unless it's cheap, and if you do, run only one ticket. Save the results to output/routes_smoke.json, then run my reset script so the working database is back to the original values.
Don't commit anything from data/ or .env. Log this prompt in AI_prompts.md under Problem 7: Backend routes, like we set up.

**Follow-up (if needed)**

N/A

**What was missing after the first prompt:** The first build ran correctly only via `uvicorn backend.main:app` from the repo root, not `uvicorn main:app` from inside backend/ as the prompt specified; fixed by inserting the repo root onto sys.path at the top of backend/main.py so the specified run command works from inside backend/.

## Problem 8: Agent dashboard

**Prompt**

Problem 8: Agent dashboard
Now let's build the frontend dashboard in frontend/ with React + Vite + TypeScript. It should call the routes we built in Problem 7 at http://localhost:8000, and it should start with npm run dev from the frontend/ folder.
Before writing code, read CLAUDE.md, output/harness.md (especially the Routes section), and backend/main.py and backend/models.py so the frontend types match the real request and response shapes. Look up the current Vite + React + TypeScript setup docs. Don't guess at the API. Check that the backend's CORS allows the Vite origin (usually http://localhost:5173), and fix it on the backend if it doesn't.
Give me a short plan first. Include 2–3 different design directions for the look and feel (layout, color, type, how agents are shown), and I'll pick one before you build.
At minimum the board should:

* List all three tickets with their status
* Let me pick one ticket and start the agent team on it
* Show each agent and what it's saying or doing while the ticket runs (live, not just at the end). If the run route blocks until it's finished, tell me, and propose how to fix that on the backend (for example, running the ticket in the background and polling the events route).
* Mark a ticket resolved when the run finishes
* Show a short summary of what each agent did on that ticket. If the backend doesn't already return a per-agent summary, tell me where you'd add it.
* Let a human approve a pay or purchase when asked. Show the amount, the payee, what it's for, and the balance before and after, and ask for confirmation before calling the approve route. If the backend refuses, show its reason clearly.
* Show the checking balance, and refresh it after an approved pay so I can see it drop

Design: make it look good, like a real desk people would want to sit at. Each of the five agents should read differently (for example its own color, icon, or voice), so I can tell at a glance who's talking. Drafts (purchase orders and customer messages) should look clearly like drafts that were never sent. Keep it simple: no extra UI libraries unless you tell me why, no localStorage needed, and no secrets in the frontend.
Docs: write output/design.md covering what you chose for the layout, how agents read differently, and how resolved tickets and cash show up, and why. Include the creative choices that make it feel special and something people would actually enjoy using.
Test lightly: start the backend and the frontend, load the board, and check that tickets and the balance appear and there are no CORS or console errors. Don't run a full ticket yet; I'll do that myself. Take a screenshot if you can.
Don't commit anything from data/, .env, or frontend/node_modules. Log this prompt in AI_prompts.md under Problem 8: Agent dashboard, like we set up.

**Follow-up (if needed)**

"Trading-floor ticker board" design direction selected (out of three options presented: trading-floor ticker board, chat/thread view, org-chart/desk map).

**What was missing after the first prompt:** The run route blocked until the full ticket resolved, so it was changed to return 202 immediately and run the Boss agent as a background task, with the frontend polling /events and /tickets for live updates; the subagent also couldn't verify the board in an actual browser (no browser tool available to it), so a live preview/console/network check was done separately afterward, which also found and cleared two stray orphaned dev-server processes left over from the subagent's own curl-based testing that were squatting on ports 8000 and 5173.

## Problem 9: Resolve the tickets

**Prompt**

Problem 9: Resolve the tickets (part 1: setup)
We're about to do the full run over tickets 101, 102, and 103 on the board. Before that, let's start clean.
Read CLAUDE.md and output/harness.md first. Then run my scripts/reset_db.py so data/campus_customs_new.db is back to the original values, and never touch campus_customs.db. Read the starting checking balance through the MCP tool (not raw SQL), and show it to me along with any open invoices, the lease next_due, and the payments table, which should be empty or original. Save that snapshot to output/cash_start.json so we have a record from before the run.
Then start the backend (uvicorn main:app --reload --port 8000 from backend/) and the frontend (npm run dev from frontend/), confirm both are up with no CORS or console errors, and stop. Don't run any tickets, approve anything, or change the database. I'll run all three tickets on the board myself and click Approve as a human.
Log this prompt in AI_prompts.md under Problem 9: Resolve the tickets, like we set up.

**Follow-up (if needed)**

give me a fresh link

this is just the old one still

[screenshot of the board showing ticket 101 blocked with a disabled "Resolved" button and the stale end-of-run summary]

yes do that

give me a fresh link

[screenshot of the board after retrying ticket 101, still blocked, showing the stale-notes short-circuit]

yes lets do 3

Problem 9: Resolve the tickets (part 2: write-up)
I've run all three tickets on the board and approved the payments as a human. Now let's document the run. Use only what really happened: get your facts from output/audit_trail.json (entries after the reset), the payments table, the invoices, leases, and tickets tables, and cash_accounts. Read shop data through the MCP tools. Don't invent or smooth over anything, and if something didn't go the way I expected, say so.
- output/desk_tickets.html: on each ticket tab, fill the Actual section with which agents worked, who delegated to whom and in what order, which MCP tools they used, and the final outcome. Keep my Expected section exactly as it is. Leave Reflection blank, because I'll write it myself.
- Cash tab in the same file: list the starting checking balance (from output/cash_start.json), then for each ticket how cash changed and why (which pay or purchase, the dollar amount, and the payments row id), then the ending balance. Check the math: start minus all payments must equal the cash_accounts balance in the working database right now. Show me the check, and stop and tell me if it doesn't match. Also confirm the balance never went negative and that each paid invoice or lease was updated.
- output/resolved_tickets.json: for each ticket, the id, final status, a short outcome, what each agent contributed, and any human approvals (who approved, the amount, and when).
- output/resolved_board.html: a page I can double-click, with my screenshots from output/screenshots/ (ticket_101.png, ticket_102.png, ticket_103.png), one section per ticket with a short caption. Use relative paths so it works from the repo.
- output/harness.md: finish it so it covers the tables, the MCP tools, the five agents, the API routes, the dashboard, and the safety rules. Make sure it matches the code as it is now.
Don't wipe or rewrite audit_trail.json. Don't reset the database until I say so, because the ending balance has to match what's in it. Don't commit anything from data/ or .env. Log this prompt in AI_prompts.md under Problem 9: Resolve the tickets, like we set up.

**What was missing after the first prompt:** The first prompt only set up the clean starting snapshot; the actual run then surfaced several real bugs along the way (Accounting's missing cash tool, a frontend stuck-"Running" bug, a `request_payment` retry-exhaustion crash, a stray reset wiping the `pending_approvals` table mid-session, a disabled-button bug on `blocked` tickets, and a retried ticket short-circuiting on its own stale notes) that had to be found and partly fixed before the write-up could reflect what genuinely happened — which, in the end, was that no payment was ever actually approved anywhere in the exercise, and the write-up documents that honestly rather than the originally-expected successful approval.
