from typing import List, Dict
from pydantic import BaseModel
from google.adk.agents import Agent
from google.adk.tools import ToolContext, FunctionTool
from google.adk.tools.agent_tool import AgentTool
from quote_agent.prompts import upsell_instructions, suggest_bundle_instructions
from quote_agent.tools.catalog import search_catalog_memory_tool
from difflib import get_close_matches


def get_bundle_label(value: str | None) -> str:
    return {
        "Structural Essentials": "🧱 Structural Kit",
        "Fire Rated Essentials": "🔥 Fire Rated Essentials",
        "Plumbing Kit": "💧 Plumbing Pack",
        "Site Prep Bundle": "🛠️ Site Prep Bundle",
        "Electrical Pack": "⚡ Electrical Kit"
    }.get(value or "", "📦 Suggested Bundle")


def map_skus_to_product_ids(catalog: List[Dict], skus: List[str]) -> List[int]:
    sku_lookup = {p["sku"]: p["id"] for p in catalog}
    return [sku_lookup[sku] for sku in skus if sku in sku_lookup]


def find_product_id_by_name(name: str, tool_context: ToolContext) -> dict:
    catalog = tool_context.state.get("catalog", [])
    name_lower = name.lower()

    for p in catalog:
        if name_lower in p.get("name", "").lower():
            return {"product_id": p["id"], "matched_name": p["name"]}

    #fuzzy title match
    names = [p["name"] for p in catalog]
    matches = get_close_matches(name, names, n=1, cutoff=0.6)
    if matches:
        matched_name = matches[0]
        matched_product = next(p for p in catalog if p["name"] == matched_name)
        return {
            "product_id": matched_product["id"],
            "matched_name": matched_name
        }

    return {"error": f"No matching product found for '{name}'"}


class ShouldOfferBundleArgs(BaseModel):
    product_ids: List[int]
    user_text: str


class ProductMetadata(BaseModel):
    id: int
    name: str
    custom_fields: List[Dict[str, str]]


class SuggestBundlesArgs(BaseModel):
    user_text: str
    products: List[ProductMetadata]


should_offer_bundle_agent = Agent(
    name="should_offer_bundle_agent",
    model="gemini-2.0-flash",
    description=
    "Decides if bundling should be offered based on user message and product metadata.",
    instruction=upsell_instructions,
)

suggest_bundle_agent = Agent(
    name="suggest_bundle_agent",
    model="gemini-2.0-flash",
    description=
    "Suggests persuasive bundles using user message and catalog metadata.",
    instruction=suggest_bundle_instructions,
    tools=[search_catalog_memory_tool])

should_offer_bundle_tool = AgentTool(agent=should_offer_bundle_agent)
suggest_bundle_tool = AgentTool(agent=suggest_bundle_agent)
find_product_id_by_name_tool = FunctionTool(func=find_product_id_by_name)

__all__ = [
    "should_offer_bundle_tool",
    "suggest_bundle_tool",
    "find_product_id_by_name_tool",
    "get_bundle_label",
    "map_skus_to_product_ids",
]
