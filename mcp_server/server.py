"""Campus Customs MCP server.

Exposes read-only tools over data/campus_customs_new.db (never the
original campus_customs.db) for the agent team to use. The database path
comes from the DATABASE_PATH env var / config.py, never hardcoded.
"""

import json
from datetime import date

from fastmcp import FastMCP

from db import execute_write, query, query_one, write_connection

mcp = FastMCP("Campus Customs")

_VALID_TICKET_STATUSES = {"open", "resolved", "waiting_on_approval", "blocked"}


def _init_tables() -> None:
    """Idempotently create tables the new write tools need.

    CREATE TABLE IF NOT EXISTS so scripts/reset_db.py (which just copies the
    original file over) is still fine - these get recreated on next startup.
    """
    with write_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                ticket_id INTEGER,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_approvals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                ref_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                account TEXT NOT NULL,
                ticket_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                approved_by TEXT
            )
            """
        )
        conn.commit()


_init_tables()


def _today() -> date:
    row = query_one("SELECT date_today FROM desk")
    return date.fromisoformat(row["date_today"])


@mcp.tool
def check_stock(sku: str, size: str | None = None, requested_qty: int | None = None) -> dict:
    """Look up inventory and pricing for a sku (optionally a specific size).

    Use this when a ticket (e.g. a customer order or a bulk discount
    request like ticket 101 or 103) names a sku and you need to know how
    much is in stock, where it is, and what it costs/sells for. Pass
    `requested_qty` to also get a shortfall flag telling you whether the
    requested amount can be filled from current stock.

    Returns one result per matching inventory row (one row per size), each
    with qty, location, unit_cost, list_price, and - if requested_qty was
    given - `in_stock` (bool) and `shortfall` (qty still needed, 0 if none).
    If the sku isn't in inventory at all, or the sku/size combination
    doesn't exist, returns a clear not-found result instead of guessing.
    """
    pricing = query_one("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,))
    if pricing is None:
        return {"found": False, "reason": f"No pricing/inventory found for sku '{sku}'."}

    if size:
        rows = query(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
            (sku, size),
        )
    else:
        rows = query(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ?",
            (sku,),
        )

    if not rows:
        return {
            "found": False,
            "reason": f"No inventory row for sku '{sku}'"
            + (f" size '{size}'" if size else "")
            + ".",
        }

    results = []
    for row in rows:
        entry = {
            **row,
            "unit_cost": pricing["unit_cost"],
            "list_price": pricing["list_price"],
        }
        if requested_qty is not None:
            entry["in_stock"] = row["qty"] >= requested_qty
            entry["shortfall"] = max(0, requested_qty - row["qty"])
        results.append(entry)

    return {"found": True, "results": results}


@mcp.tool
def check_vendor_status(vendor_id: int | None = None, vendor_name: str | None = None) -> dict:
    """Look up a vendor's lead time and whether they can currently ship.

    Use this once you know (or suspect) which vendor would restock a sku -
    for example after check_stock shows a shortfall, or after finding a
    vendor_id via a ticket's linked invoice (as with ticket 101). Pass
    either vendor_id or vendor_name (vendor_name does a case-insensitive
    exact match).

    A vendor cannot ship while they have any invoice with status 'open' -
    this tool checks that directly against the invoices table and returns
    `can_ship` (bool) plus the list of open invoices blocking them, if any.
    If no matching vendor exists, returns a clear not-found result.
    """
    if vendor_id is not None:
        vendor = query_one("SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,))
    elif vendor_name is not None:
        vendor = query_one(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE lower(name) = lower(?)",
            (vendor_name,),
        )
    else:
        return {"found": False, "reason": "Provide either vendor_id or vendor_name."}

    if vendor is None:
        identifier = vendor_id if vendor_id is not None else vendor_name
        return {"found": False, "reason": f"No vendor found for '{identifier}'."}

    open_invoices = query(
        "SELECT id, amount, due_date, description FROM invoices WHERE vendor_id = ? AND status = 'open'",
        (vendor["id"],),
    )

    return {
        "found": True,
        "vendor": vendor,
        "can_ship": len(open_invoices) == 0,
        "open_invoices": open_invoices,
    }


@mcp.tool
def check_lease_and_cash(lease_id: int) -> dict:
    """Look up a lease's rent, due status, and whether cash covers it.

    Use this for lease/rent-related tickets (like ticket 102) to find the
    monthly rent, compare its next_due date against desk.date_today to
    report whether it's overdue, due soon, or not yet due, and check that
    amount against the current cash_accounts balance.

    Returns `days_until_due` (negative if overdue), `status` (one of
    "overdue", "due_today", "upcoming"), and `cash_covers_rent` (bool).
    If the lease_id doesn't exist, returns a clear not-found result.
    """
    lease = query_one(
        "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
        (lease_id,),
    )
    if lease is None:
        return {"found": False, "reason": f"No lease found for lease_id {lease_id}."}

    cash = query_one("SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'")

    today = _today()
    due = date.fromisoformat(lease["next_due"])
    days_until_due = (due - today).days

    if days_until_due < 0:
        status = "overdue"
    elif days_until_due == 0:
        status = "due_today"
    else:
        status = "upcoming"

    return {
        "found": True,
        "lease": lease,
        "date_today": today.isoformat(),
        "days_until_due": days_until_due,
        "status": status,
        "cash_account": cash,
        "cash_covers_rent": cash is not None and cash["balance"] >= lease["monthly_rent"],
    }


@mcp.tool
def list_open_tickets() -> dict:
    """List every ticket with status='open'.

    Use this when you (the Boss) need to see what's waiting to be worked,
    rather than looking up one ticket at a time. Returns one summary row
    per open ticket (id, type, requester, subject, and the linked ids).
    """
    rows = query(
        """
        SELECT id, type, requester, subject, sku, size, qty, lease_id,
               invoice_id, status, created_at
        FROM tickets WHERE status = 'open'
        """
    )
    return {"count": len(rows), "tickets": rows}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Get the full row for one ticket by id.

    Use this to read everything about a specific ticket (type, requester,
    subject, sku, size, qty, lease_id, invoice_id, status, notes,
    created_at) before deciding who should work it. Returns a clear
    not-found result if the id doesn't exist.
    """
    row = query_one("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if row is None:
        return {"found": False, "reason": f"No ticket found with id {ticket_id}."}
    return {"found": True, "ticket": row}


@mcp.tool
def get_invoice(invoice_id: int) -> dict:
    """Get the full row for one invoice, joined with the vendor's name.

    Use this to confirm an invoice's amount, due_date, status, and which
    vendor it belongs to. Returns a clear not-found result if the id
    doesn't exist.
    """
    row = query_one(
        """
        SELECT invoices.*, vendors.name AS vendor_name
        FROM invoices JOIN vendors ON vendors.id = invoices.vendor_id
        WHERE invoices.id = ?
        """,
        (invoice_id,),
    )
    if row is None:
        return {"found": False, "reason": f"No invoice found with id {invoice_id}."}
    return {"found": True, "invoice": row}


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, note: str) -> dict:
    """Update a ticket's status and append a note explaining why.

    Use this once an agent/the Boss has made a decision about a ticket.
    `status` must be one of: open, resolved, waiting_on_approval, blocked.
    Refuses if the ticket doesn't exist or the status isn't one of those.
    The note is appended to the ticket's existing notes (not overwritten).
    """
    if status not in _VALID_TICKET_STATUSES:
        return {
            "ok": False,
            "reason": f"Invalid status '{status}'. Must be one of {sorted(_VALID_TICKET_STATUSES)}.",
        }
    existing = query_one("SELECT notes FROM tickets WHERE id = ?", (ticket_id,))
    if existing is None:
        return {"ok": False, "reason": f"No ticket found with id {ticket_id}."}

    old_notes = existing["notes"] or ""
    new_notes = f"{old_notes}\n[status -> {status}] {note}".strip()
    execute_write(
        "UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
        (status, new_notes, ticket_id),
    )
    return {"ok": True, "ticket_id": ticket_id, "status": status, "notes": new_notes}


@mcp.tool
def draft_purchase_order(
    ticket_id: int, sku: str, size: str, qty: int, vendor_id: int, lead_days: int, estimated_cost: float
) -> dict:
    """Create a DRAFT purchase order. This never places a real order.

    Use this once Inventory has confirmed a vendor can ship (no open
    unpaid invoice). The draft is stored on the board (drafts table) for
    a human to review; it does not touch invoices or vendors.
    """
    payload = {
        "ticket_id": ticket_id,
        "sku": sku,
        "size": size,
        "qty": qty,
        "vendor_id": vendor_id,
        "lead_days": lead_days,
        "estimated_cost": estimated_cost,
    }
    created_at = _today().isoformat()
    draft_id = execute_write(
        "INSERT INTO drafts (kind, ticket_id, payload, created_at) VALUES (?, ?, ?, ?)",
        ("purchase_order", ticket_id, json.dumps(payload), created_at),
    )
    return {"ok": True, "draft_id": draft_id, "payload": payload}


@mcp.tool
def draft_customer_message(ticket_id: int, message: str, facts_used: str) -> dict:
    """Create a DRAFT customer message. This never sends anything.

    Use this once Customer Service has written a message grounded in
    real tool facts. The draft is stored on the board (drafts table) for
    a human to review/send manually; nothing is emailed.
    """
    payload = {"ticket_id": ticket_id, "message": message, "facts_used": facts_used}
    created_at = _today().isoformat()
    draft_id = execute_write(
        "INSERT INTO drafts (kind, ticket_id, payload, created_at) VALUES (?, ?, ?, ?)",
        ("customer_message", ticket_id, json.dumps(payload), created_at),
    )
    return {"ok": True, "draft_id": draft_id, "payload": payload}


@mcp.tool
def request_payment(kind: str, ref_id: int, amount: float, account: str, ticket_id: int | None = None) -> dict:
    """Create a PENDING payment approval. This never moves money.

    Use this when Accounting has confirmed cash covers an invoice or
    lease payment. `kind` must be 'invoice' or 'lease'. Refuses if the
    account's balance can't cover the amount (so a request that could
    never be approved is never created) - no money moves either way.
    """
    if kind not in ("invoice", "lease"):
        return {"ok": False, "reason": "kind must be 'invoice' or 'lease'."}

    cash = query_one("SELECT name, balance FROM cash_accounts WHERE name = ?", (account,))
    if cash is None:
        return {"ok": False, "reason": f"No cash account named '{account}'."}
    if cash["balance"] < amount:
        return {
            "ok": False,
            "reason": f"Insufficient cash: balance {cash['balance']} < requested {amount}.",
        }

    created_at = _today().isoformat()
    approval_id = execute_write(
        """
        INSERT INTO pending_approvals (kind, ref_id, amount, account, ticket_id, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """,
        (kind, ref_id, amount, account, ticket_id, created_at),
    )
    return {
        "ok": True,
        "approval_id": approval_id,
        "status": "pending",
        "note": "No money has moved. A human must approve this before anything is paid.",
    }


@mcp.tool
def list_pending_approvals() -> dict:
    """List every pending_approvals row with status='pending'.

    Use this (from the backend, not any agent - no agent has this tool
    wired in) to show a human what payments are waiting on their
    approval before execute_approved_payment can move any money.
    """
    rows = query(
        """
        SELECT id, kind, ref_id, amount, account, ticket_id, status, created_at, approved_by
        FROM pending_approvals WHERE status = 'pending'
        """
    )
    return {"count": len(rows), "approvals": rows}


@mcp.tool
def get_cash_balance(account: str = "checking") -> dict:
    """Look up the current balance for a cash account (default 'checking').

    Use this for a quick, direct read of cash on hand without pulling in
    an unrelated lease. Returns a clear not-found result if the account
    doesn't exist.
    """
    cash = query_one("SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account,))
    if cash is None:
        return {"found": False, "reason": f"No cash account named '{account}'."}
    return {"found": True, "cash_account": cash}


@mcp.tool
def execute_approved_payment(approval_id: int, approved_by: str) -> dict:
    """Move money for an already-approved payment. The ONLY tool that can.

    NOT attached to any agent's toolset - this exists for a future
    backend-only caller after a human approves a pending_approvals row.
    Refuses if the approval doesn't exist, isn't pending, approved_by is
    blank, or cash is (re-checked, right now) insufficient. On success,
    atomically: records a payment, decrements cash, marks the invoice
    paid (if kind='invoice'), and marks the approval 'approved'.
    """
    if not approved_by or not approved_by.strip():
        return {"ok": False, "reason": "approved_by is required."}

    with write_connection() as conn:
        try:
            approval = conn.execute(
                "SELECT * FROM pending_approvals WHERE id = ?", (approval_id,)
            ).fetchone()
            if approval is None:
                return {"ok": False, "reason": f"No pending_approvals row with id {approval_id}."}
            if approval["status"] != "pending":
                return {"ok": False, "reason": f"Approval {approval_id} is not pending (status={approval['status']})."}

            cash = conn.execute(
                "SELECT balance FROM cash_accounts WHERE name = ?", (approval["account"],)
            ).fetchone()
            if cash is None:
                return {"ok": False, "reason": f"No cash account named '{approval['account']}'."}
            if cash["balance"] < approval["amount"]:
                return {
                    "ok": False,
                    "reason": f"Insufficient cash at execution time: balance {cash['balance']} < {approval['amount']}.",
                }

            today = conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]

            conn.execute(
                "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
                (approval["kind"], approval["ref_id"], approval["amount"], approval["account"], today, approved_by),
            )
            conn.execute(
                "UPDATE cash_accounts SET balance = balance - ? WHERE name = ?",
                (approval["amount"], approval["account"]),
            )
            if approval["kind"] == "invoice":
                conn.execute(
                    "UPDATE invoices SET status = 'paid' WHERE id = ?", (approval["ref_id"],)
                )
            conn.execute(
                "UPDATE pending_approvals SET status = 'approved', approved_by = ? WHERE id = ?",
                (approved_by, approval_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return {"ok": True, "approval_id": approval_id, "kind": approval["kind"], "amount": approval["amount"]}


if __name__ == "__main__":
    mcp.run()
