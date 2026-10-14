"""Single shared MCP toolset pointed at the local stdio FastMCP server.

Each agent gets a tool-filtered view of this same toolset via `.filtered()`
rather than each agent opening its own duplicate server process definition.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic_ai._run_context import RunContext
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.toolsets.abstract import ToolsetTool
from pydantic_ai.toolsets.wrapper import WrapperToolset

from backend.audit import append_audit_entry

ROOT = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = ROOT / "mcp_server" / "server.py"

# One shared toolset instance; agents narrow it with .filtered(...).
# Pass a Path (not a string) to avoid FastMCP's deprecated string-inference.
# max_retries=3 (default is 1): a malformed tool-call argument on the first
# attempt otherwise exhausts the retry budget immediately and crashes the
# whole ticket run (seen on request_payment during the Problem 9 run) -
# raising this gives the model a couple of chances to self-correct its
# arguments before PydanticAI gives up and raises UnexpectedModelBehavior.
campus_customs_toolset = MCPToolset(SERVER_SCRIPT, max_retries=3)


@dataclass
class AuditedToolset(WrapperToolset):
    """Wraps a (filtered) toolset to log every individual MCP tool call.

    Closes the gap flagged since Problem 8: only delegations and an agent's
    final_result were ever logged, so a malformed/failed tool call (like the
    request_payment retry-exhaustion crash on ticket 101) left no record of
    what args were actually sent. Per this package's own guidance, this is a
    WrapperToolset subclass rather than a change to MCPToolset/FilteredToolset
    themselves, so it applies as a thin cross-cutting layer.
    """

    agent_name: str = ""

    async def call_tool(
        self, name: str, tool_args: dict[str, Any], ctx: RunContext[Any], tool: ToolsetTool[Any]
    ) -> Any:
        ticket_id = getattr(ctx.deps, "ticket_id", None)
        try:
            result = await super().call_tool(name, tool_args, ctx, tool)
        except Exception as exc:
            append_audit_entry(
                ticket_id,
                self.agent_name,
                "tool_call",
                tool_name=name,
                args_summary=tool_args,
                result_summary=f"error: {exc}",
            )
            raise
        append_audit_entry(
            ticket_id,
            self.agent_name,
            "tool_call",
            tool_name=name,
            args_summary=tool_args,
            result_summary=result,
        )
        return result


def restricted_toolset(allowed_tool_names: set[str], agent_name: str):
    """Return a view of the shared toolset exposing only the named tools,
    with every call to it logged to the audit trail under `agent_name`."""

    def _filter(ctx, tool_def):
        return tool_def.name in allowed_tool_names

    filtered = campus_customs_toolset.filtered(_filter)
    return AuditedToolset(wrapped=filtered, agent_name=agent_name)
