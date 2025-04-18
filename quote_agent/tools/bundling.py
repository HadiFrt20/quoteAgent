from typing import List, Dict
from pydantic import BaseModel
from google.adk.agents import Agent
from google.adk.tools import ToolContext, FunctionTool
from google.adk.tools.agent_tool import AgentTool
from quote_agent.prompts import upsell_instructions


# 🏷️ Label helper (optional UI usage)
def get_bundle_label(value: str | None) -> str:
    return {
        "Structural Essentials": "🧱 Structural Kit",
        "Fire Rated Essentials": "🔥 Fire Rated Essentials",
        "Plumbing Kit": "💧 Plumbing Pack",
        "Site Prep Bundle": "🛠️ Site Prep Bundle",
        "Electrical Pack": "⚡ Electrical Kit"
    }.get(value or "", "📦 Suggested Bundle")


# 🔍 Helper: map SKUs → product IDs
def map_skus_to_product_ids(catalog: List[Dict], skus: List[str]) -> List[int]:
    sku_lookup = {p["sku"]: p["id"] for p in catalog}
    return [sku_lookup[sku] for sku in skus if sku in sku_lookup]


# 🔍 Helper: fuzzy match product by name
def find_product_id_by_name(name: str, tool_context: ToolContext) -> dict:
    catalog = tool_context.state.get("catalog", [])
    name_lower = name.lower()
    for p in catalog:
        if name_lower in p.get("name", "").lower():
            return {"product_id": p["id"], "matched_name": p["name"]}
    return {"error": f"No matching product found for '{name}'"}


# 📦 Model for bundle decision
class ShouldOfferBundleArgs(BaseModel):
    product_ids: List[int]
    user_text: str


# 📦 Model for upsell suggestion
class ProductMetadata(BaseModel):
    id: int
    name: str
    custom_fields: List[Dict[str, str]]


class SuggestBundlesArgs(BaseModel):
    user_text: str
    products: List[ProductMetadata]


# 🤖 LLM agent: decide if bundling is relevant
should_offer_bundle_agent = Agent(
    name="should_offer_bundle_agent",
    model="gemini-2.0-flash",
    description=
    "Decides if bundling should be offered based on user message and product metadata.",
    instruction=upsell_instructions,
)

# 🤖 LLM agent: suggest relevant bundles
suggest_bundle_agent = Agent(
    name="suggest_bundle_agent",
    model="gemini-2.0-flash",
    description=
    "Suggests persuasive bundles using user message and list of products with custom fields.",
    instruction="""
You're a smart upselling agent.

Use:
- The user message
- A list of products (each with name and custom_fields like BUNDLE_TYPE, PROJECT_TYPE, USAGE_CLASS, MATERIAL_GROUP)

Suggest 1–3 persuasive bundles that:
- Save time
- Improve compatibility
- Reduce trips or costs
- Are tailored to project types or industries

Respond in plain English. Use emojis and label kits clearly:
- 💧 Plumbing Pack: for copper pipes and fittings
- 🔥 Fire Rated Essentials: includes fire-resistant drywall, foam, insulation
""")

# 🔧 Expose as callable tools
should_offer_bundle_tool = AgentTool(agent=should_offer_bundle_agent)
suggest_bundle_tool = AgentTool(agent=suggest_bundle_agent)
find_product_id_by_name_tool = FunctionTool(func=find_product_id_by_name)

__all__ = [
    "should_offer_bundle_tool",
    "suggest_bundle_tool",
    "find_product_id_by_name_tool",
]
