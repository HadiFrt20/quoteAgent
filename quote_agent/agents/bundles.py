from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext, FunctionTool
from typing import List
from quote_agent.prompts import bundle_agent_instructions
from quote_agent.tools.bundling import (
    suggest_bundle_tool,
    find_product_id_by_name_tool,
)
from quote_agent.tools.catalog import read_catalog_from_state_tool
from google.adk.memory.base_memory_service import MemoryResult


def search_catalog_memory(query: str,
                          tool_context: ToolContext) -> List[MemoryResult]:
    """Searches the product catalog stored in memory using semantic keyword matching."""
    results = tool_context.search_memory(query)
    if results and results.memories:
        return results.memories
    return []


search_catalog_memory_tool = FunctionTool(func=search_catalog_memory)

bundle_agent = LlmAgent(
    name="bundle_agent",
    model="gemini-2.0-flash",
    instruction=bundle_agent_instructions,
    description=("Recommends related SKUs using catalog metadata "
                 "(bundle type, project type, usage class, material group)."),
    tools=[
        suggest_bundle_tool,
        find_product_id_by_name_tool,
        read_catalog_from_state_tool,
        search_catalog_memory,
    ],
)
