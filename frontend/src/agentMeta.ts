// Color + icon mapping for the five agents (plus human/system entries that
// also appear in the audit trail), so the wire feed is scannable at a glance.
// Documented in output/design.md.

export interface AgentMeta {
  label: string;
  icon: string;
  color: string;
}

export const AGENT_META: Record<string, AgentMeta> = {
  boss: { label: "Boss", icon: "\u{1F451}", color: "#e6c66b" }, // crown, gold
  inventory: { label: "Inventory", icon: "\u{1F4E6}", color: "#5bc0de" }, // box, cyan-blue
  accounting: { label: "Accounting", icon: "\u{1F4B0}", color: "#4caf50" }, // money bag, green
  facilities: { label: "Facilities", icon: "\u{1F3E2}", color: "#ff8a3d" }, // building, orange
  customer_service: { label: "Customer Service", icon: "\u{1F4AC}", color: "#c77dff" }, // speech bubble, purple
  human: { label: "Human", icon: "\u{1F9D1}", color: "#eef2f7" },
  system: { label: "System", icon: "⚙", color: "#93a8c2" },
};

export function metaFor(agent: string): AgentMeta {
  return (
    AGENT_META[agent] ?? {
      label: agent,
      icon: "•",
      color: "#93a8c2",
    }
  );
}
