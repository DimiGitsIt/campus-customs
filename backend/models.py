"""Pydantic models shared across agents: delegation envelopes, tool-result
shapes, and each agent's structured output type."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DelegationRequest(BaseModel):
    target_agent: str
    request: str
    ticket_id: int | None = None


class DelegationResult(BaseModel):
    agent: str
    summary: str
    facts: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)


class PaymentRequestResult(BaseModel):
    ok: bool
    approval_id: int | None = None
    reason: str | None = None


class PurchaseOrderDraftResult(BaseModel):
    ok: bool
    draft_id: int | None = None
    reason: str | None = None


class CustomerMessageDraftResult(BaseModel):
    ok: bool
    draft_id: int | None = None
    reason: str | None = None


class InventoryResult(BaseModel):
    sku: str | None = None
    size: str | None = None
    on_hand_qty: int | None = None
    needed_qty: int | None = None
    shortfall: int | None = None
    vendor_options: list[str] = Field(default_factory=list)
    estimated_cost: float | None = None
    draft_po_id: int | None = None
    blockers: list[str] = Field(default_factory=list)


class AccountingResult(BaseModel):
    amount: float | None = None
    due_date: str | None = None
    overdue: bool | None = None
    cash_before: float | None = None
    cash_after: float | None = None
    fits: bool | None = None
    pending_approval_id: int | None = None
    recommendation: str | None = None


class FacilitiesResult(BaseModel):
    space: str | None = None
    landlord: str | None = None
    monthly_rent: float | None = None
    due_date: str | None = None
    status: str | None = None
    cash_coverage: bool | None = None
    next_step: str | None = None


class CustomerServiceResult(BaseModel):
    draft_text: str | None = None
    ticket_id: int | None = None
    facts_relied_on: list[str] = Field(default_factory=list)


class TicketDecision(BaseModel):
    ticket_id: int
    status: str
    agents_used: list[str] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)
    next_steps: str | None = None


class BossResult(TicketDecision):
    pass


# --- FastAPI backend request/response models (backend/main.py) ---


class TicketSummary(BaseModel):
    ticket_id: int
    type: str | None = None
    subject: str | None = None
    requester: str | None = None
    status: str


class AuditEvent(BaseModel):
    timestamp: str
    ticket_id: int | None = None
    agent: str
    step_type: str
    tool_name: str | None = None
    args_summary: str | None = None
    result_summary: str | None = None
    usage: dict | None = None
    stop_reason: str | None = None


class AuditEventListResponse(BaseModel):
    count: int
    events: list[AuditEvent]


class PendingApproval(BaseModel):
    id: int
    kind: str
    ref_id: int
    amount: float
    account: str
    ticket_id: int | None = None
    status: str
    created_at: str
    approved_by: str | None = None


class PendingApprovalListResponse(BaseModel):
    count: int
    approvals: list[PendingApproval]


class ApproveRequest(BaseModel):
    approved_by: str = Field(..., min_length=1)


class ApproveResponse(BaseModel):
    ok: bool
    approval_id: int
    kind: str | None = None
    amount: float | None = None
    reason: str | None = None


class CashBalanceResponse(BaseModel):
    account: str
    balance: float
    date: str | None = None


class ResetResponse(BaseModel):
    ok: bool
    message: str
