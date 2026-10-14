import { useState } from "react";
import type { PendingApproval } from "../types";
import { approvePayment } from "../api";

interface Props {
  approvals: PendingApproval[];
  cashBalance: number | null;
  onApproved: () => void;
}

function humanLabel(a: PendingApproval): string {
  if (a.kind === "invoice") return `Invoice #${a.ref_id}`;
  if (a.kind === "rent" || a.kind === "lease") return `Lease #${a.ref_id} rent`;
  return `${a.kind} #${a.ref_id}`;
}

function ApprovalCard({ a, cashBalance, onApproved }: Props & { a: PendingApproval }) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const after = cashBalance != null ? cashBalance - a.amount : null;

  async function doApprove() {
    setBusy(true);
    setError(null);
    try {
      await approvePayment(a.id, "dimitri.watat@yale.edu");
      setConfirming(false);
      onApproved();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="approval-card">
      <div className="amount">${a.amount.toFixed(2)}</div>
      <div className="purpose">{humanLabel(a)}</div>
      <div className="account">from account: {a.account}</div>
      {!confirming && (
        <button className="approve-btn" onClick={() => setConfirming(true)} disabled={busy}>
          Approve
        </button>
      )}
      {confirming && (
        <div className="confirm-box">
          <div className="row-line">
            <span>Payee / purpose</span>
            <span>{humanLabel(a)}</span>
          </div>
          <div className="row-line">
            <span>Amount</span>
            <span>${a.amount.toFixed(2)}</span>
          </div>
          <div className="row-line">
            <span>Current balance</span>
            <span>{cashBalance != null ? `$${cashBalance.toFixed(2)}` : "unknown"}</span>
          </div>
          <div className="row-line">
            <span>Balance if approved</span>
            <span className="after">{after != null ? `$${after.toFixed(2)}` : "unknown"}</span>
          </div>
          <div className="confirm-actions">
            <button className="approve-btn" onClick={doApprove} disabled={busy}>
              {busy ? "Submitting…" : "Confirm payment"}
            </button>
            <button className="cancel-btn" onClick={() => setConfirming(false)} disabled={busy}>
              Cancel
            </button>
          </div>
        </div>
      )}
      {error && <div className="error-text">{error}</div>}
    </div>
  );
}

export default function ApprovalsPanel({ approvals, cashBalance, onApproved }: Props) {
  if (approvals.length === 0) {
    return <div className="empty-note">No pending approvals.</div>;
  }
  return (
    <div>
      {approvals.map((a) => (
        <ApprovalCard key={a.id} a={a} approvals={approvals} cashBalance={cashBalance} onApproved={onApproved} />
      ))}
    </div>
  );
}
