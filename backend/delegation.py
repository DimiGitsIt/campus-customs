"""Shared ticket context + delegation guardrails.

`TicketContext` is threaded through every agent run as `deps`. It carries
the shared `RunUsage` object (so `UsageLimits` applies across the whole
ticket, not per-agent-call), the current delegation depth, and the set of
agents already working this ticket (to block cycles).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from pydantic_ai import RunContext
from pydantic_ai.usage import RunUsage

from backend.audit import append_audit_entry

MAX_DELEGATION_DEPTH = 3


@dataclass
class TicketContext:
    ticket_id: int | None
    depth: int = 0
    visited_agents: frozenset[str] = field(default_factory=frozenset)
    usage: RunUsage = field(default_factory=RunUsage)
    max_depth: int = MAX_DELEGATION_DEPTH


async def delegate(ctx: RunContext[TicketContext], from_agent: str, target_agent: str, request: str) -> str:
    """Shared delegation implementation used by every delegate_to_* tool.

    Refuses (returns a string, never raises) on depth overrun or a cycle.
    Otherwise builds a child TicketContext, runs the target agent with the
    SAME shared usage object, and records an audit entry either way.
    """
    deps = ctx.deps

    if deps.depth >= deps.max_depth:
        reason = f"Delegation refused: max delegation depth ({deps.max_depth}) reached."
        append_audit_entry(deps.ticket_id, from_agent, "delegation", tool_name=f"delegate_to_{target_agent}",
                            args_summary=request, result_summary=reason)
        return reason

    if target_agent in deps.visited_agents:
        reason = f"Delegation refused: '{target_agent}' is already working this ticket (would create a loop)."
        append_audit_entry(deps.ticket_id, from_agent, "delegation", tool_name=f"delegate_to_{target_agent}",
                            args_summary=request, result_summary=reason)
        return reason

    # Lazy import to dodge circular imports between agent modules and the registry.
    from backend.registry import get_agent

    target = get_agent(target_agent)
    if target is None:
        reason = f"Delegation refused: unknown agent '{target_agent}'."
        append_audit_entry(deps.ticket_id, from_agent, "delegation", tool_name=f"delegate_to_{target_agent}",
                            args_summary=request, result_summary=reason)
        return reason

    child_deps = replace(
        deps,
        depth=deps.depth + 1,
        visited_agents=deps.visited_agents | {from_agent, target_agent},
    )

    append_audit_entry(deps.ticket_id, from_agent, "delegation", tool_name=f"delegate_to_{target_agent}",
                        args_summary=request, result_summary="dispatched")

    result = await target.run(request, deps=child_deps, usage=deps.usage, message_history=None)

    append_audit_entry(
        deps.ticket_id,
        target_agent,
        "final_result",
        tool_name=None,
        args_summary=request,
        result_summary=str(result.output),
        usage=result.usage,
    )

    return str(result.output)
