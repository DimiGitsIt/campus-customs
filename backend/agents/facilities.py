from __future__ import annotations

from pydantic_ai import Agent, RunContext

from backend.delegation import TicketContext, delegate
from backend.mcp_toolset import restricted_toolset
from backend.model_config import get_model
from backend.models import FacilitiesResult
from backend.prompts import load_instructions
from backend.registry import register_agent

# request_payment is NOT included here: Facilities must delegate to
# Accounting for any payment, never request one itself.
ALLOWED_TOOLS = {"check_lease_and_cash", "update_ticket_status"}

facilities_agent = Agent(
    get_model(),
    name="facilities",
    deps_type=TicketContext,
    output_type=FacilitiesResult,
    instructions=load_instructions("facilities.md"),
    toolsets=[restricted_toolset(ALLOWED_TOOLS, "facilities")],
)


@facilities_agent.tool
async def delegate_to_boss(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Boss agent."""
    return await delegate(ctx, "facilities", "boss", request)


@facilities_agent.tool
async def delegate_to_inventory(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Inventory agent."""
    return await delegate(ctx, "facilities", "inventory", request)


@facilities_agent.tool
async def delegate_to_accounting(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a payment request (e.g. rent) to the Accounting agent."""
    return await delegate(ctx, "facilities", "accounting", request)


@facilities_agent.tool
async def delegate_to_customer_service(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Customer Service agent."""
    return await delegate(ctx, "facilities", "customer_service", request)


register_agent("facilities", facilities_agent)
