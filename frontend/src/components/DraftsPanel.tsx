import type { AuditEvent } from "../types";

interface Props {
  events: AuditEvent[];
}

interface CustomerDraft {
  ticketId: number | null;
  text: string;
  timestamp: string;
}

interface PoNote {
  ticketId: number | null;
  timestamp: string;
  resultSummary: string | null;
}

// CustomerServiceResult is stringified by Python's default BaseModel repr as
// something like: "draft_text='...' ticket_id=101 facts_relied_on=['...']"
// We only have that raw string (result_summary on the customer_service
// agent's final_result audit entry) to work with — there's no dedicated
// /drafts route. See output/design.md for the full explanation of this gap.
function extractDraftText(resultSummary: string | null): string | null {
  if (!resultSummary) return null;
  const match = resultSummary.match(/draft_text=(['"])([\s\S]*?)\1\s+ticket_id=/);
  if (match) return match[2];
  // Fallback: if truncation cut off before ticket_id, just show from draft_text= onward.
  const loose = resultSummary.match(/draft_text=(['"])([\s\S]*)/);
  return loose ? loose[2] : null;
}

export default function DraftsPanel({ events }: Props) {
  const customerFinals = events.filter(
    (e) => e.agent === "customer_service" && e.step_type === "final_result"
  );
  const drafts: CustomerDraft[] = customerFinals
    .map((e) => {
      const text = extractDraftText(e.result_summary);
      return text ? { ticketId: e.ticket_id, text, timestamp: e.timestamp } : null;
    })
    .filter((d): d is CustomerDraft => d !== null);

  const poFinals = events.filter((e) => e.agent === "inventory" && e.step_type === "final_result");
  const poNotes: PoNote[] = poFinals
    .filter((e) => /draft_po_id=(?!None)/.test(e.result_summary ?? ""))
    .map((e) => ({ ticketId: e.ticket_id, timestamp: e.timestamp, resultSummary: e.result_summary }));

  if (drafts.length === 0 && poNotes.length === 0) {
    return <div className="empty-note">No drafts produced yet.</div>;
  }

  return (
    <div>
      {drafts.map((d, i) => (
        <div className="draft-card" key={`cs-${i}`}>
          <span className="draft-badge">Draft — never sent</span>
          <div className="draft-meta">
            Customer message for ticket #{d.ticketId ?? "?"} · {new Date(d.timestamp).toLocaleTimeString()}
          </div>
          <div className="draft-text">{d.text}</div>
        </div>
      ))}
      {poNotes.map((p, i) => (
        <div className="draft-card" key={`po-${i}`}>
          <span className="draft-badge">Draft — never sent</span>
          <div className="draft-meta">
            Purchase order draft for ticket #{p.ticketId ?? "?"} · {new Date(p.timestamp).toLocaleTimeString()}
          </div>
          <div className="draft-text">
            A purchase-order draft was created (see draft_po_id in the inventory agent's result below), but the
            current API/audit trail only exposes the numeric id, not the draft's line-item text. This is a
            documented gap — see output/design.md.
          </div>
          <div className="draft-meta">{p.resultSummary}</div>
        </div>
      ))}
    </div>
  );
}
