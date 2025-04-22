from google.adk.agents import LlmAgent
from quote_agent.prompts import root_instructions
#from quote_agent.agents.intent import intent_agent
from quote_agent.agents.orders import order_agent
from quote_agent.agents.bundles import bundle_agent
from quote_agent.agents.negotiation import negotiation_agent
from quote_agent.lifecycle import preload_agent_context

#intent_agent.output_key = "user_intent"

root_agent = LlmAgent(
    name="quote_negotiation_assistant",
    model="gemini-2.0-flash",
    description=
    "Routes user input to the correct sales agent: order, bundle, or quote.",
    instruction=root_instructions,
    sub_agents=[
        #intent_agent,
        order_agent,
        bundle_agent,
        negotiation_agent,
    ],
    before_agent_callback=preload_agent_context,
)
