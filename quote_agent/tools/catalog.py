import os
import uuid
import requests
from time import sleep
from typing import List

from google.adk.tools import ToolContext, FunctionTool
from google.adk.events import Event
from google.genai.types import Content, Part
from google.adk.sessions import Session
from google.adk.memory import InMemoryMemoryService

# Long-term memory for catalog entries
memory_service = InMemoryMemoryService()

# Storefront GraphQL endpoint for BigCommerce
STOREFRONT_GRAPHQL_ENDPOINT = f"https://store-{os.environ.get('BIGCOMMERCE_STORE_HASH', 'MISSING')}.mybigcommerce.com/graphql"


def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def _load_catalog_data() -> List[dict]:
    token = os.environ.get("BIGCOMMERCE_STOREFRONT_API_TOKEN")
    if not token:
        print("❌ BIGCOMMERCE_STOREFRONT_API_TOKEN is missing.")
        return []

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    query = """
    query getProductsByEntityIds($entityIds: [Int!]!) {
      site {
        products(entityIds: $entityIds) {
          edges {
            node {
              entityId
              name
              sku
              description
              path
              defaultImage {
                url640wide: url(width: 640)
              }
              prices {
                price {
                  value
                  currencyCode
                }
              }
              customFields {
                edges {
                  node {
                    name
                    value
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    entity_ids = list(range(34596, 34696))  # Example range
    all_products = []

    for batch in chunked(entity_ids, 10):
        try:
            res = requests.post(STOREFRONT_GRAPHQL_ENDPOINT,
                                headers=headers,
                                json={
                                    "query": query,
                                    "variables": {
                                        "entityIds": batch
                                    }
                                })
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"❌ Error fetching batch {batch}: {e}")
            continue

        products = data.get("data", {}).get("site",
                                            {}).get("products",
                                                    {}).get("edges", [])
        for edge in products:
            node = edge.get("node", {})
            price = ((node.get("prices") or {}).get("price")
                     or {}).get("value")
            currency = ((node.get("prices") or {}).get("price")
                        or {}).get("currencyCode")

            custom_fields = [
                {
                    "name": cf["node"]["name"],
                    "value": cf["node"]["value"]
                } for cf in node.get("customFields", {}).get("edges", [])
                if cf.get("node", {}).get("name") and cf["node"].get("value")
            ]

            product = {
                "id": node.get("entityId"),
                "name": node.get("name"),
                "sku": node.get("sku"),
                "path": node.get("path"),
                "image": (node.get("defaultImage") or {}).get("url640wide"),
                "price": price,
                "currency": currency,
                "description": node.get("description", "").strip(),
                "custom_fields": custom_fields
            }
            all_products.append(product)
        sleep(0.01)

    print(f"✅ Loaded {len(all_products)} products.")
    return all_products


def preload_customer_catalog(tool_context):
    if "catalog" in tool_context.state:
        return {"status": "already_loaded"}
    catalog = _load_catalog_data()
    tool_context.state["catalog"] = catalog
    return {"status": "catalog_loaded", "count": len(catalog)}


def read_catalog_from_state(tool_context: ToolContext) -> Content:
    catalog = tool_context.state.get("catalog", [])
    if not catalog:
        return Content(role="user",
                       parts=[Part(text="❌ No catalog in session state.")])

    lines = []
    for product in catalog[:25]:
        lines.append(
            f"🛍️ {product['name']} (SKU: {product['sku']}) — {product['currency']} {product['price']}"
        )
        if product.get("description"):
            lines.append(f"📝 {product['description']}")
        if product.get("image"):
            lines.append(f"🖼️ {product['image']}")
    return Content(role="user", parts=[Part(text="\n".join(lines))])


def ingest_catalog_to_memory(app_name: str, user_id: str, session_id: str):
    catalog = _load_catalog_data()
    events = []

    for product in catalog:
        lines = [f"{product['name']}"]
        if product.get("sku"):
            lines.append(f"SKU: {product['sku']}")
        if product.get("price"):
            lines.append(f"Price: {product['currency']} {product['price']}")
        if product.get("custom_fields"):
            for cf in product["custom_fields"]:
                lines.append(f"{cf['name']}: {cf['value']}")
        if product.get("description"):
            lines.append(product["description"])

        content = Content(role="user", parts=[Part(text="\n".join(lines))])
        events.append(Event(author="catalog_ingest", content=content))

    session = Session(id=f"catalog-{uuid.uuid4()}",
                      app_name=app_name,
                      user_id=user_id,
                      state={},
                      events=events)

    memory_service.add_session_to_memory(session)
    print(f"✅ Catalog ingested into memory ({len(events)} entries).")
    return {"status": "catalog_ingested", "entries": len(events)}


# Expose as tools
preload_customer_catalog_tool = FunctionTool(func=preload_customer_catalog)
read_catalog_from_state_tool = FunctionTool(func=read_catalog_from_state)

__all__ = [
    "preload_customer_catalog_tool", "read_catalog_from_state_tool",
    "ingest_catalog_to_memory", "memory_service"
]
