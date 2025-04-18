from google.adk.agents import LlmAgent
from quote_agent.prompts import order_agent_instructions
from quote_agent.tools.orders import (
    get_last_order_tool,
    get_order_products_tool,
    get_order_products_by_ids_tool,
    read_order_history_tool,
    resolve_order_ids_tool,
)
from quote_agent.tools.bundling import should_offer_bundle_tool

order_agent = LlmAgent(
    name="order_agent",
    model="gemini-2.0-flash",
    description="Handles order history, reorders, and order product lookups.",
    instruction=order_agent_instructions,
    tools=[
        get_last_order_tool,
        get_order_products_tool,
        get_order_products_by_ids_tool,
        read_order_history_tool,
        resolve_order_ids_tool,
        should_offer_bundle_tool,
    ])
