from __future__ import annotations

from pydantic_ai import Agent, RunContext

from backend.delegation import TicketContext, delegate
from backend.mcp_toolset import restricted_toolset
from backend.model_config import get_model
from backend.models import AccountingResult
from backend.prompts import load_instructions
from backend.registry import register_agent

ALLOWED_TOOLS = {
    "get_invoice",
    "check_vendor_status",
    "check_stock",
    "check_lease_and_cash",
    "get_cash_balance",
    "request_payment",
    "update_ticket_status",
}

accounting_agent = Agent(
    get_model(),
    name="accounting",
    deps_type=TicketContext,
    output_type=AccountingResult,
    instructions=load_instructions("accounting.md"),
    toolsets=[restricted_toolset(ALLOWED_TOOLS, "accounting")],
)


@accounting_agent.tool
async def delegate_to_boss(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Boss agent."""
    return await delegate(ctx, "accounting", "boss", request)


@accounting_agent.tool
async def delegate_to_inventory(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Inventory agent."""
    return await delegate(ctx, "accounting", "inventory", request)


@accounting_agent.tool
async def delegate_to_facilities(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Facilities agent."""
    return await delegate(ctx, "accounting", "facilities", request)


@accounting_agent.tool
async def delegate_to_customer_service(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Customer Service agent."""
    return await delegate(ctx, "accounting", "customer_service", request)


register_agent("accounting", accounting_agent)
