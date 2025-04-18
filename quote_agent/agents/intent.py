from google.adk.agents import LlmAgent
from quote_agent.prompts import intent_instructions

INTENT_LABELS = [
    "order_reorder", "bundle_suggestion", "quote_request", "catalog_lookup",
    "order_history", "other"
]

intent_agent = LlmAgent(
    name="intent_agent",
    model="gemini-2.0-flash",
    description=
    "Classifies user intent for routing (e.g. reorder, bundle, quote).",
    instruction=(intent_instructions),
    output_key="user_intent")
