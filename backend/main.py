"""FastAPI backend for Campus Customs.

Wires the MCP-backed agent team (backend/registry.py) and the shared MCP
toolset (backend/mcp_toolset.py) to HTTP routes for the React dashboard.

MCP connection lifecycle: the shared `campus_customs_toolset` is entered
once in the app's lifespan context manager and kept open for the whole
process. `MCPToolset.__aenter__`/`__aexit__` are reference-counted (see
`pydantic_ai/mcp.py`), so holding it open here does not conflict with each
agent run's own `async with` over the same toolset instance during a
`/tickets/{id}/run` call - it's the same shared stdio subprocess connection
either way, not a second one. Routes that need a single MCP tool call
directly (not through an agent) use `campus_customs_toolset.direct_call_tool`.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Lets `uvicorn main:app --reload --port 8000` work when started from inside
# backend/ (as specified for this problem): every module in this package
# imports via the `backend.` prefix, which requires the repo root (this
# folder's parent) on sys.path, not just backend/ itself. uvicorn only adds
# the cwd (backend/) to sys.path, so add the parent explicitly before any
# `backend.*` import below.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.audit import AUDIT_PATH, append_audit_entry
from backend.delegation import TicketContext
from backend.mcp_toolset import campus_customs_toolset
from backend.models import (
    ApproveRequest,
    ApproveResponse,
    AuditEvent,
    AuditEventListResponse,
    BossResult,
    CashBalanceResponse,
    PendingApproval,
    PendingApprovalListResponse,
    ResetResponse,
    TicketSummary,
)
from backend.registry import get_agent

ROOT = Path(__file__).resolve().parent.parent
RESET_SCRIPT = ROOT / "scripts" / "reset_db.py"

KNOWN_TICKET_IDS = (101, 102, 103)

# Tracks in-flight background ticket runs so a second POST /tickets/{id}/run
# while one is already running doesn't double-fire the agent team.
# Values: "running" | "done" | "error".
_RUN_STATE: dict[int, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with campus_customs_toolset:
        yield


app = FastAPI(title="Campus Customs Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Vite's default dev-server port for the React dashboard (next problem).
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _call_tool(name: str, args: dict | None = None):
    """Call one MCP tool directly (no agent involved) and return its payload."""
    return await campus_customs_toolset.direct_call_tool(name, args or {})


async def _get_ticket_or_404(ticket_id: int) -> dict:
    result = await _call_tool("get_ticket", {"ticket_id": ticket_id})
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("reason", f"Ticket {ticket_id} not found."))
    return result["ticket"]


@app.get("/tickets", response_model=list[TicketSummary])
async def list_tickets():
    """Return tickets 101-103 with their current status, via get_ticket (MCP)."""
    summaries: list[TicketSummary] = []
    for ticket_id in KNOWN_TICKET_IDS:
        result = await _call_tool("get_ticket", {"ticket_id": ticket_id})
        if not result.get("found"):
            continue
        ticket = result["ticket"]
        summaries.append(
            TicketSummary(
                ticket_id=ticket["id"],
                type=ticket.get("type"),
                subject=ticket.get("subject"),
                requester=ticket.get("requester"),
                status=ticket["status"],
            )
        )
    return summaries


async def _run_ticket_background(ticket_id: int) -> None:
    """Run the Boss agent for a ticket in the background and record the outcome.

    Each delegated agent's own final_result/delegation steps are already
    logged by backend.delegation.delegate(), but the Boss's own top-level
    completion was never logged anywhere durable (only kept in the in-memory
    _RUN_STATE dict, which resets on backend restart) - this function now
    appends that entry itself, on both success and crash, so the audit trail
    always has a definitive last word for a ticket's run.
    """
    try:
        boss_agent = get_agent("boss")
        deps = TicketContext(ticket_id=ticket_id)
        result = await boss_agent.run(f"Resolve ticket {ticket_id}.", deps=deps)
        _RUN_STATE[ticket_id] = {"status": "done", "result": result.output.model_dump()}
        append_audit_entry(
            ticket_id=ticket_id,
            agent_name="boss",
            step_type="final_result",
            tool_name=None,
            args_summary=None,
            result_summary=result.output,
            usage=result.usage,
        )
    except Exception as exc:  # noqa: BLE001 - want to surface any agent-run crash
        _RUN_STATE[ticket_id] = {"status": "error", "error": str(exc)}
        append_audit_entry(
            ticket_id=ticket_id,
            agent_name="boss",
            step_type="final_result",
            tool_name=None,
            args_summary=None,
            result_summary=f"Background agent run crashed: {exc}",
        )


@app.post("/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int):
    """Kick off the Boss agent for a ticket as a background task and return immediately.

    Returns 202 with {"ticket_id", "status": "running"} right away. If a run
    for this ticket is already in flight, returns the same shape without
    starting a second one. Existence of the ticket is still checked
    synchronously first (404 if unknown), matching the prior behavior.
    """
    # Cheap existence check via MCP before spinning up any agent run.
    await _get_ticket_or_404(ticket_id)

    existing = _RUN_STATE.get(ticket_id)
    if existing and existing.get("status") == "running":
        return {"ticket_id": ticket_id, "status": "running", "detail": "Already running."}

    _RUN_STATE[ticket_id] = {"status": "running"}
    asyncio.create_task(_run_ticket_background(ticket_id))
    return {"ticket_id": ticket_id, "status": "running"}


@app.get("/tickets/{ticket_id}/run-status")
async def run_status(ticket_id: int):
    """Surface background-run state not otherwise derivable from /events + /tickets

    (specifically: an agent run crashing with an exception before it could
    write a final_result entry). Returns {"status": "idle"} if /run was never
    called for this ticket_id in this process's lifetime.
    """
    state = _RUN_STATE.get(ticket_id, {"status": "idle"})
    return {"ticket_id": ticket_id, **state}


@app.get("/events", response_model=AuditEventListResponse)
async def list_events(limit: int = 50):
    """Return the most recent `limit` audit trail entries (output/audit_trail.json)."""
    if not AUDIT_PATH.exists():
        return AuditEventListResponse(count=0, events=[])
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = []
    if not isinstance(data, list):
        data = []
    recent = list(reversed(data))[:limit]
    events = [AuditEvent(**entry) for entry in recent]
    return AuditEventListResponse(count=len(events), events=events)


@app.get("/approvals", response_model=PendingApprovalListResponse)
async def list_approvals():
    """List pending payment approvals via the list_pending_approvals MCP tool."""
    result = await _call_tool("list_pending_approvals")
    approvals = [PendingApproval(**row) for row in result.get("approvals", [])]
    return PendingApprovalListResponse(count=len(approvals), approvals=approvals)


@app.post("/approvals/{approval_id}/approve", response_model=ApproveResponse)
async def approve_payment(approval_id: int, body: ApproveRequest):
    """Human-approve a pending payment; the only route allowed to call execute_approved_payment."""
    result = await _call_tool(
        "execute_approved_payment", {"approval_id": approval_id, "approved_by": body.approved_by}
    )

    if not result.get("ok"):
        reason = result.get("reason", "Payment could not be executed.")
        append_audit_entry(
            ticket_id=None,
            agent_name="human",
            step_type="payment_refused",
            tool_name="execute_approved_payment",
            args_summary={"approval_id": approval_id, "approved_by": body.approved_by},
            result_summary=reason,
        )
        raise HTTPException(status_code=400, detail=reason)

    # Best-effort: look up the ticket_id tied to this approval for the audit entry.
    ticket_id = None
    approvals = (await _call_tool("list_pending_approvals")).get("approvals", [])
    for row in approvals:
        if row["id"] == approval_id:
            ticket_id = row.get("ticket_id")
            break

    append_audit_entry(
        ticket_id=ticket_id,
        agent_name="human",
        step_type="payment_executed",
        tool_name="execute_approved_payment",
        args_summary={"approval_id": approval_id, "approved_by": body.approved_by},
        result_summary=result,
    )
    return ApproveResponse(
        ok=True, approval_id=approval_id, kind=result.get("kind"), amount=result.get("amount")
    )


@app.get("/cash", response_model=CashBalanceResponse)
async def get_cash():
    """Return the current checking account balance via the get_cash_balance MCP tool."""
    result = await _call_tool("get_cash_balance", {"account": "checking"})
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("reason", "Cash account not found."))
    account = result["cash_account"]
    return CashBalanceResponse(account=account["name"], balance=account["balance"], date=account.get("date"))


@app.post("/reset", response_model=ResetResponse)
async def reset_database():
    """Reset data/campus_customs_new.db to the original values via scripts/reset_db.py."""
    subprocess.run([sys.executable, str(RESET_SCRIPT)], check=True)
    append_audit_entry(
        ticket_id=None,
        agent_name="system",
        step_type="reset",
        result_summary="database reset to original values via scripts/reset_db.py",
    )
    return ResetResponse(ok=True, message="Database reset to original values.")
