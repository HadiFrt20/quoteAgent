from google.adk.agents import LlmAgent
from quote_agent.prompts import bundle_agent_instructions
from quote_agent.tools.bundling import (
    suggest_bundle_tool,
    find_product_id_by_name_tool,
)
from quote_agent.tools.catalog import read_catalog_from_state_tool
from quote_agent.tools.catalog import search_catalog_memory_tool
from quote_agent.tools.catalog import get_price_by_product_id_tool

bundle_agent = LlmAgent(
    name="bundle_agent",
    model="gemini-2.0-flash",
    instruction=bundle_agent_instructions,
    description=("Recommends related SKUs using catalog metadata "
                 "(bundle type, project type, usage class, material group)."),
    tools=[
        suggest_bundle_tool, find_product_id_by_name_tool,
        read_catalog_from_state_tool, search_catalog_memory_tool,
        get_price_by_product_id_tool
    ],
)
