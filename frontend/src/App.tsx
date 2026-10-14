import { useCallback, useEffect, useState } from "react";
import "./App.css";
import { getApprovals, getCash, getEvents, getRunStatus, getTickets, runTicket } from "./api";
import type { AuditEvent, BossResult, CashBalanceResponse, PendingApproval, TicketSummary } from "./types";
import TicketBoard from "./components/TicketBoard";
import WireFeed from "./components/WireFeed";
import ApprovalsPanel from "./components/ApprovalsPanel";
import DraftsPanel from "./components/DraftsPanel";

const FAST_POLL_MS = 1500;
const SLOW_POLL_MS = 6000;

function App() {
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);
  const [cash, setCash] = useState<CashBalanceResponse | null>(null);
  const [runningIds, setRunningIds] = useState<Set<number>>(new Set());
  // End-of-run summaries come from GET /tickets/{id}/run-status once a run
  // reaches "done" (its `result` field is the Boss's full BossResult).
  const [summaries, setSummaries] = useState<Record<number, BossResult | undefined>>({});
  const [loadError, setLoadError] = useState<string | null>(null);

  const refreshTickets = useCallback(async () => {
    const data = await getTickets();
    setTickets(data);
  }, []);

  // The authoritative "is this ticket's run finished" signal is
  // /tickets/{id}/run-status, not the ticket's own status field: a ticket
  // can finish its run and legitimately stay "open" (e.g. rent isn't due
  // yet, so Facilities/Boss decide not to act yet) rather than flipping to
  // resolved/blocked. Checking status alone left a finished run showing
  // "Running..." forever.
  const pollRunStatuses = useCallback(async (ids: Set<number>) => {
    if (ids.size === 0) return;
    await Promise.all(
      Array.from(ids).map(async (ticketId) => {
        try {
          const status = await getRunStatus(ticketId);
          if (status.status === "done" || status.status === "error") {
            setRunningIds((prev) => {
              const next = new Set(prev);
              next.delete(ticketId);
              return next;
            });
            if (status.status === "done" && status.result) {
              setSummaries((prev) => ({ ...prev, [ticketId]: status.result }));
            }
            if (status.status === "error") {
              setLoadError(`Ticket ${ticketId} run failed: ${status.error ?? "unknown error"}`);
            }
          }
        } catch {
          // A transient run-status failure shouldn't clear "running" state;
          // the next poll tick will try again.
        }
      })
    );
  }, []);

  const refreshEvents = useCallback(async () => {
    const data = await getEvents(150);
    setEvents(data.events);
  }, []);

  const refreshApprovals = useCallback(async () => {
    const data = await getApprovals();
    setApprovals(data.approvals);
  }, []);

  const refreshCash = useCallback(async () => {
    const data = await getCash();
    setCash(data);
  }, []);

  const refreshAll = useCallback(async () => {
    try {
      await Promise.all([refreshTickets(), refreshEvents(), refreshApprovals(), refreshCash()]);
      setLoadError(null);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : String(e));
    }
  }, [refreshTickets, refreshEvents, refreshApprovals, refreshCash]);

  // Initial load.
  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  // Poll faster while something is running, slower otherwise. While a
  // ticket is running, also poll its /run-status directly so completion is
  // detected even when the ticket's own status field doesn't change.
  useEffect(() => {
    const interval = setInterval(
      () => {
        refreshEvents();
        refreshTickets();
        refreshApprovals();
        pollRunStatuses(runningIds);
      },
      runningIds.size > 0 ? FAST_POLL_MS : SLOW_POLL_MS
    );
    return () => clearInterval(interval);
  }, [runningIds, refreshEvents, refreshTickets, refreshApprovals, pollRunStatuses]);

  async function handleRun(ticketId: number) {
    setRunningIds((prev) => new Set(prev).add(ticketId));
    try {
      await runTicket(ticketId);
      // Also do one quick check shortly after dispatch, in case the run
      // finishes (as ticket 102's did) well before the next slow-poll tick.
      setTimeout(() => pollRunStatuses(new Set([ticketId])), FAST_POLL_MS);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : String(e));
      setRunningIds((prev) => {
        const next = new Set(prev);
        next.delete(ticketId);
        return next;
      });
    }
  }

  async function handleApproved() {
    await Promise.all([refreshApprovals(), refreshCash(), refreshEvents()]);
  }

  // Wire feed should read chronologically (oldest at top, newest at bottom)
  // like a real ticker; /events comes back newest-first.
  const chronologicalEvents = [...events].reverse();

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Campus Customs — Desk Floor</h1>
          <p className="subtitle">Multi-agent ticket desk, live</p>
        </div>
        <div className="cash-balance">
          <div className="label">Checking balance</div>
          <div className="amount">{cash != null ? `$${cash.balance.toFixed(2)}` : "—"}</div>
          <button className="reset-btn" onClick={() => refreshAll()}>
            Refresh
          </button>
        </div>
      </header>

      {loadError && <div className="error-text" style={{ padding: "0 28px" }}>{loadError}</div>}

      <div className="app-body">
        <section>
          <h2 className="section-title">Tickets</h2>
          <TicketBoard
            tickets={tickets}
            runningIds={runningIds}
            summaries={summaries}
            events={events}
            onRun={handleRun}
          />
        </section>

        <div className="row">
          <div className="column">
            <h2 className="section-title">Pending Approvals</h2>
            <ApprovalsPanel
              approvals={approvals}
              cashBalance={cash?.balance ?? null}
              onApproved={handleApproved}
            />
          </div>
          <div className="column">
            <h2 className="section-title">Drafts</h2>
            <DraftsPanel events={events} />
          </div>
        </div>

        <section>
          <h2 className="section-title">Wire</h2>
          <WireFeed events={chronologicalEvents} />
        </section>
      </div>
    </div>
  );
}

export default App;
