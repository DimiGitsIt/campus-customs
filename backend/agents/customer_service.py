from __future__ import annotations

from pydantic_ai import Agent, RunContext

from backend.delegation import TicketContext, delegate
from backend.mcp_toolset import restricted_toolset
from backend.model_config import get_model
from backend.models import CustomerServiceResult
from backend.prompts import load_instructions
from backend.registry import register_agent

ALLOWED_TOOLS = {"get_ticket", "draft_customer_message", "check_stock", "check_vendor_status", "update_ticket_status"}

customer_service_agent = Agent(
    get_model(),
    name="customer_service",
    deps_type=TicketContext,
    output_type=CustomerServiceResult,
    instructions=load_instructions("customer_service.md"),
    toolsets=[restricted_toolset(ALLOWED_TOOLS, "customer_service")],
)


@customer_service_agent.tool
async def delegate_to_boss(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question or sub-task to the Boss agent."""
    return await delegate(ctx, "customer_service", "boss", request)


@customer_service_agent.tool
async def delegate_to_inventory(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question (e.g. stock/lead time facts) to the Inventory agent."""
    return await delegate(ctx, "customer_service", "inventory", request)


@customer_service_agent.tool
async def delegate_to_accounting(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question to the Accounting agent."""
    return await delegate(ctx, "customer_service", "accounting", request)


@customer_service_agent.tool
async def delegate_to_facilities(ctx: RunContext[TicketContext], request: str) -> str:
    """Delegate a question to the Facilities agent."""
    return await delegate(ctx, "customer_service", "facilities", request)


register_agent("customer_service", customer_service_agent)
