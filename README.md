# Campus Customs — Multi-Agent Operations

A multi-agent back office for a small college merch shop: five PydanticAI agents (Boss, Inventory, Accounting, Facilities, Customer Service) work tickets using a shared MCP server over a SQLite database, with a FastAPI backend and a React dashboard for a human to watch the agents and approve payments.

See `output/harness.md` for the full data/tool/agent/route reference, `output/design.md` for the dashboard's design rationale, and `AI_prompts.md` for the prompt history behind this build.

## 1. Clone and install

```bash
git clone <this-repo-url>
cd <repo-folder>
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

## 2. Configure your environment

```bash
cp .env.example .env
```

Open `.env` and set `PORTKEY_API_KEY` to your own Portkey key. Leave `MODEL_NAME=gpt-6-luna` and `DATABASE_PATH=data/campus_customs_new.db` as they are — `gpt-6-luna` is the only model used anywhere in this project.

## 3. Get a clean working database

The repo ships with both `data/campus_customs.db` (the original, untouched) and `data/campus_customs_new.db` (the working copy, committed in whatever state the last run left it in). To start from a known-clean state before running your own tickets:

```bash
python scripts/reset_db.py
```

This overwrites `data/campus_customs_new.db` from `data/campus_customs.db`. **Never edit or overwrite `data/campus_customs.db` itself** — every tool, agent, and route in this project is hard-wired to read/write only the working copy via the `DATABASE_PATH` env var.

## 4. Start the MCP server

The agents and the backend launch `mcp_server/server.py` themselves as a stdio subprocess (see `backend/mcp_toolset.py`) — you don't need to start it by hand to run the agent team or the dashboard. If you want to sanity-check it on its own:

```bash
cd mcp_server
python server.py
```

`.mcp.json` at the repo root also registers it as a project MCP server (relative paths only) if you want to call its tools directly from a Claude Code session.

## 5. Start the FastAPI backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Confirm it's up: `curl http://localhost:8000/tickets` should return the three seed tickets.

## 6. Start the React dashboard

In a separate terminal:

```bash
cd frontend
npm run dev
```

Open the URL Vite prints (defaults to `http://localhost:5173`) to see the desk board. The backend's CORS is configured for exactly this origin.

## 7. Before a full three-ticket run

If you want to replay all three tickets from the original seed data (rather than whatever state is currently committed), reset first:

```bash
python scripts/reset_db.py
```

Then use the dashboard's Run button on each ticket and Approve any pending payment as the human-in-the-loop. **Never run the reset script against, or otherwise touch, `data/campus_customs.db`.**

## Project layout

- `mcp_server/` — the MCP server and its own README
- `backend/` — FastAPI app, the five PydanticAI agents, prompts, models, audit trail
- `frontend/` — the React + Vite + TypeScript dashboard
- `data/` — `campus_customs.db` (original, read-only) and `campus_customs_new.db` (working copy)
- `output/` — generated docs and run artifacts (`harness.md`, `design.md`, `desk_tickets.html`, `resolved_tickets.json`, `resolved_board.html`, `audit_trail.json`, etc.)
- `scripts/reset_db.py` — restores the working copy from the original
