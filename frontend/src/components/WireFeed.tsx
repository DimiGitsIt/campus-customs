import type { AuditEvent } from "../types";
import { metaFor } from "../agentMeta";

interface Props {
  events: AuditEvent[];
}

export default function WireFeed({ events }: Props) {
  if (events.length === 0) {
    return (
      <div className="wire-feed">
        <div className="wire-empty">No activity yet — run a ticket to see the desk come alive.</div>
      </div>
    );
  }

  return (
    <div className="wire-feed">
      {events.map((e, i) => {
        const meta = metaFor(e.agent);
        const ticketTag = e.ticket_id != null ? `#${e.ticket_id}` : "—";
        return (
          <div className="wire-row" key={i}>
            <span className="ts">{new Date(e.timestamp).toLocaleTimeString()}</span>
            <span className="agent-tag" style={{ color: meta.color }}>
              {meta.icon} {meta.label}
            </span>
            <span className="step">
              {ticketTag} · {e.step_type}
              {e.tool_name ? ` · ${e.tool_name}` : ""}
            </span>
            <span className="summary">{e.result_summary ?? e.args_summary ?? ""}</span>
          </div>
        );
      })}
    </div>
  );
}
