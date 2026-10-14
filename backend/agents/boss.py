from __future__ import annotations

from pydantic_ai import Agent, RunContext

from backend.delegation import TicketContext, delegate
from backend.mcp_toolset import restricted_toolset
from backend.model_config import get_model
from backend.models import BossResult
from backend.prompts import load_instructions
from backend.registry import register_agent

ALLOWED_TOOLS = {"get_ticket", "list_open_tickets", "update_ticket_status"}

boss_agent = Agent(
    get_model(),
    name="boss",
    deps_type=TicketContext,
    output_type=BossResult,
    instructions=load_instructions("boss.md"),
    toolsets=[restricted_toolset(ALLOWED_TOOLS, "boss")],
)


@boss_agent.tool
async def delegate_to_inventory(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a stock/restock question to the Inventory agent."""
    return await delegate(ctx, "boss", "inventory", request)


@boss_agent.tool
async def delegate_to_accounting(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a cash/invoice/payment question to the Accounting agent."""
    return await delegate(ctx, "boss", "accounting", request)


@boss_agent.tool
async def delegate_to_facilities(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a lease/rent question to the Facilities agent."""
    return await delegate(ctx, "boss", "facilities", request)


@boss_agent.tool
async def delegate_to_customer_service(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a customer-reply task to the Customer Service agent."""
    return await delegate(ctx, "boss", "customer_service", request)


register_agent("boss", boss_agent)
