// All backend calls, pointed at the FastAPI server. No API keys live here —
// the frontend never needs one, it only talks to localhost:8000.
import type {
  ApproveResponse,
  AuditEventListResponse,
  CashBalanceResponse,
  PendingApprovalListResponse,
  ResetResponse,
  RunStatusResponse,
  RunTicketResponse,
  TicketSummary,
} from "./types";

const BASE_URL = "http://localhost:8000";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore parse failure, fall back to generic message
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function getTickets(): Promise<TicketSummary[]> {
  return fetch(`${BASE_URL}/tickets`).then((r) => handle(r));
}

export function runTicket(ticketId: number): Promise<RunTicketResponse> {
  return fetch(`${BASE_URL}/tickets/${ticketId}/run`, { method: "POST" }).then((r) => handle(r));
}

export function getRunStatus(ticketId: number): Promise<RunStatusResponse> {
  return fetch(`${BASE_URL}/tickets/${ticketId}/run-status`).then((r) => handle(r));
}

export function getEvents(limit = 100): Promise<AuditEventListResponse> {
  return fetch(`${BASE_URL}/events?limit=${limit}`).then((r) => handle(r));
}

export function getApprovals(): Promise<PendingApprovalListResponse> {
  return fetch(`${BASE_URL}/approvals`).then((r) => handle(r));
}

export function approvePayment(approvalId: number, approvedBy: string): Promise<ApproveResponse> {
  return fetch(`${BASE_URL}/approvals/${approvalId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved_by: approvedBy }),
  }).then((r) => handle(r));
}

export function getCash(): Promise<CashBalanceResponse> {
  return fetch(`${BASE_URL}/cash`).then((r) => handle(r));
}

export function resetDatabase(): Promise<ResetResponse> {
  return fetch(`${BASE_URL}/reset`, { method: "POST" }).then((r) => handle(r));
}
