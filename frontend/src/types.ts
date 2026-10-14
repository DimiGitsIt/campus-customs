// Mirrors backend/models.py response shapes exactly (field names/types).

export interface TicketSummary {
  ticket_id: number;
  type: string | null;
  subject: string | null;
  requester: string | null;
  status: string;
}

export interface AuditEvent {
  timestamp: string;
  ticket_id: number | null;
  agent: string;
  step_type: string; // model_call | tool_call | delegation | final_result | payment_executed | payment_refused | reset
  tool_name: string | null;
  args_summary: string | null;
  result_summary: string | null;
  usage: Record<string, unknown> | null;
  stop_reason: string | null;
}

export interface AuditEventListResponse {
  count: number;
  events: AuditEvent[];
}

export interface PendingApproval {
  id: number;
  kind: string;
  ref_id: number;
  amount: number;
  account: string;
  ticket_id: number | null;
  status: string;
  created_at: string;
  approved_by: string | null;
}

export interface PendingApprovalListResponse {
  count: number;
  approvals: PendingApproval[];
}

export interface ApproveRequest {
  approved_by: string;
}

export interface ApproveResponse {
  ok: boolean;
  approval_id: number;
  kind: string | null;
  amount: number | null;
  reason: string | null;
}

export interface CashBalanceResponse {
  account: string;
  balance: number;
  date: string | null;
}

export interface ResetResponse {
  ok: boolean;
  message: string;
}

// POST /tickets/{id}/run now returns 202 immediately (see backend async fix)
export interface RunTicketResponse {
  ticket_id: number;
  status: string; // "running"
  detail?: string;
}

// GET /tickets/{id}/run-status
export interface RunStatusResponse {
  ticket_id: number;
  status: "idle" | "running" | "done" | "error";
  result?: BossResult;
  error?: string;
}

// Boss agent's structured final output (backend/models.py TicketDecision/BossResult)
export interface BossResult {
  ticket_id: number;
  status: string;
  agents_used: string[];
  key_facts: string[];
  actions_taken: string[];
  next_steps: string | null;
}
