from google.adk.agents import LlmAgent
from quote_agent.prompts import negotiation_agent_instructions
from quote_agent.tools.bundling import find_product_id_by_name_tool
from quote_agent.tools.create_discounted_order import create_multi_item_discounted_order_tool
from quote_agent.tools.create_quote import create_combined_quote_request_tool_func
from quote_agent.tools.catalog import get_price_by_product_id_tool

negotiation_agent = LlmAgent(
    name="negotiation_agent",
    model="gemini-2.0-flash",
    instruction=negotiation_agent_instructions,
    description=
    "Handles pricing requests, applies discounts, or escalates to quote creation if discount >10%.",
    tools=[
        create_multi_item_discounted_order_tool,
        create_combined_quote_request_tool_func, find_product_id_by_name_tool,
        get_price_by_product_id_tool
    ],
)
