import type { AuditEvent, BossResult, TicketSummary } from "../types";

interface Props {
  tickets: TicketSummary[];
  runningIds: Set<number>;
  summaries: Record<number, BossResult | undefined>;
  events: AuditEvent[];
  onRun: (ticketId: number) => void;
}

function buildFallbackSummary(ticketId: number, events: AuditEvent[]): BossResult | null {
  // If the backend run's structured BossResult isn't in hand (e.g. page was
  // open before the run started), reconstruct a lightweight summary from the
  // boss's own final_result audit entry for this ticket.
  const bossFinal = events.find(
    (e) => e.ticket_id === ticketId && e.agent === "boss" && e.step_type === "final_result"
  );
  if (!bossFinal) return null;
  const agentsUsed = Array.from(
    new Set(
      events
        .filter((e) => e.ticket_id === ticketId && e.step_type === "final_result")
        .map((e) => e.agent)
    )
  );
  return {
    ticket_id: ticketId,
    status: "resolved",
    agents_used: agentsUsed,
    key_facts: [],
    actions_taken: [],
    next_steps: bossFinal.result_summary,
  };
}

export default function TicketBoard({ tickets, runningIds, summaries, events, onRun }: Props) {
  return (
    <div className="ticket-grid">
      {tickets.map((t) => {
        // "resolved" (for styling/pill purposes) is any non-open status.
        // Only a literally "resolved" ticket is done-done; "blocked" means
        // the run finished but didn't succeed, and must stay re-runnable
        // from the board (e.g. after a transient backend error), not look
        // permanently stuck like a true resolution.
        const resolved = t.status !== "open";
        const terminal = t.status === "resolved";
        const running = runningIds.has(t.ticket_id);
        const summary = summaries[t.ticket_id] ?? (resolved ? buildFallbackSummary(t.ticket_id, events) : null);
        return (
          <div
            key={t.ticket_id}
            className={`ticket-card${resolved ? " resolved" : ""}${running ? " selected" : ""}`}
          >
            <div className="ticket-card-top">
              <div>
                <div className="ticket-id">#{t.ticket_id}</div>
                <div className="ticket-type">{t.type ?? "unknown"}</div>
              </div>
              <span className={`status-pill ${resolved ? "resolved" : "open"}`}>
                {resolved ? t.status : "open"}
              </span>
            </div>
            <div className="ticket-subject">{t.subject ?? "(no subject)"}</div>
            <div className="ticket-requester">Requested by {t.requester ?? "unknown"}</div>
            <button
              className={`run-btn${running ? " running" : ""}`}
              disabled={running || terminal}
              onClick={() => onRun(t.ticket_id)}
            >
              {running ? "Running…" : terminal ? "Resolved" : t.status === "blocked" ? "Retry" : "Run"}
            </button>
            {summary && (
              <div className="ticket-summary">
                <div className="summary-label">End-of-run summary</div>
                {summary.agents_used.length > 0 && (
                  <div>Agents used: {summary.agents_used.join(", ")}</div>
                )}
                {summary.key_facts.length > 0 && (
                  <>
                    <div className="summary-label">Key facts</div>
                    <ul>
                      {summary.key_facts.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </>
                )}
                {summary.actions_taken.length > 0 && (
                  <>
                    <div className="summary-label">Actions taken</div>
                    <ul>
                      {summary.actions_taken.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </>
                )}
                {summary.next_steps && <div>Next: {summary.next_steps}</div>}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
