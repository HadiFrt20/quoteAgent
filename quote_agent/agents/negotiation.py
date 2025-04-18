from google.adk.agents import LlmAgent
from quote_agent.prompts import negotiation_agent_instructions

from quote_agent.tools.create_discounted_order import create_discounted_order_tool
from quote_agent.tools.create_quote import create_quote_request_tool

negotiation_agent = LlmAgent(
    name="negotiation_agent",
    model="gemini-2.0-flash",
    instruction=negotiation_agent_instructions,
    description=
    "Handles pricing requests, applies discounts, or escalates to quote creation if discount >10%.",
    tools=[
        create_discounted_order_tool,
        create_quote_request_tool,
    ],
)
