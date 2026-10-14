from __future__ import annotations

from pydantic_ai import Agent, RunContext

from backend.delegation import TicketContext, delegate
from backend.mcp_toolset import restricted_toolset
from backend.model_config import get_model
from backend.models import InventoryResult
from backend.prompts import load_instructions
from backend.registry import register_agent

ALLOWED_TOOLS = {"check_stock", "check_vendor_status", "get_invoice", "draft_purchase_order", "update_ticket_status"}

inventory_agent = Agent(
    get_model(),
    name="inventory",
    deps_type=TicketContext,
    output_type=InventoryResult,
    instructions=load_instructions("inventory.md"),
    toolsets=[restricted_toolset(ALLOWED_TOOLS, "inventory")],
)


@inventory_agent.tool
async def delegate_to_boss(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Boss agent."""
    return await delegate(ctx, "inventory", "boss", request)


@inventory_agent.tool
async def delegate_to_accounting(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Accounting agent."""
    return await delegate(ctx, "inventory", "accounting", request)


@inventory_agent.tool
async def delegate_to_facilities(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Facilities agent."""
    return await delegate(ctx, "inventory", "facilities", request)


@inventory_agent.tool
async def delegate_to_customer_service(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Customer Service agent."""
    return await delegate(ctx, "inventory", "customer_service", request)


register_agent("inventory", inventory_agent)
