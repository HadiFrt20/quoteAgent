from typing import Dict, List, Optional
from google.adk.tools import ToolContext, FunctionTool
from google.adk.agents.callback_context import CallbackContext
from google.genai.types import Content, Part
import requests
import os
import re
from datetime import datetime
from email.utils import format_datetime

B2B_GRAPHQL_ENDPOINT = "https://api-b2b.bigcommerce.com/graphql"
STOREFRONT_GRAPHQL_ENDPOINT = f"https://store-{os.environ['BIGCOMMERCE_STORE_HASH']}.mybigcommerce.com/graphql"


def get_last_order(tool_context: ToolContext) -> Dict:
    token = tool_context.state.get("b2b_storefront_token")
    if not token:
        return {
            "status": "error",
            "error_message": "Missing B2B storefront token in state."
        }

    company_id = 2164075
    query = """
    query GetOrders($companyId: Int!) {
      allOrders(companyIds: [$companyId], first: 1, orderBy: "-bcOrderId") {
        edges {
          node {
            orderId
            createdAt
            totalIncTax
            currencyCode
            status
            poNumber
            companyInfo { companyName }
          }
        }
      }
    }
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        res = requests.post(B2B_GRAPHQL_ENDPOINT,
                            json={
                                "query": query,
                                "variables": {
                                    "companyId": company_id
                                }
                            },
                            headers=headers)
        data = res.json()
        if "errors" in data:
            return {"status": "error", "error_message": str(data["errors"])}
        order = data["data"]["allOrders"]["edges"][0]["node"]
        tool_context.state["last_order"] = order
        dt = datetime.utcfromtimestamp(int(order["createdAt"]))
        return {
            "status": "success",
            "order": {
                "orderId": order["orderId"],
                "createdAt": format_datetime(dt),
                "totalIncTax": order["totalIncTax"],
                "status": order["status"],
                "poNumber": order.get("poNumber"),
                "companyName": order.get("companyInfo", {}).get("companyName"),
                "currencyCode": order["currencyCode"]
            }
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


get_last_order_tool = FunctionTool(func=get_last_order)


def get_order_products(tool_context: ToolContext) -> Content:
    token = tool_context.state.get("b2b_storefront_token")
    if not token:
        return Content(
            role="user",
            parts=[Part(text="❌ Missing B2B token in session state.")])

    last_order = tool_context.state.get("last_order")
    if not last_order:
        return Content(role="user",
                       parts=[Part(text="❌ No last order found.")])

    order_id = last_order.get("orderId")
    if not order_id:
        return Content(role="user", parts=[Part(text="❌ Missing order ID.")])

    query = """
    query GetOrderProducts($bcOrderId: Int!) {
      orderProducts(bcOrderId: $bcOrderId) {
        notes
        quantity
        productId
        variantId
        optionList
      }
    }
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        res = requests.post(B2B_GRAPHQL_ENDPOINT,
                            json={
                                "query": query,
                                "variables": {
                                    "bcOrderId": int(order_id)
                                }
                            },
                            headers=headers)
        data = res.json()
        products = data.get("data", {}).get("orderProducts", [])
        if not products:
            return Content(role="user",
                           parts=[Part(text="No products found.")])

        # Get product details from Storefront API
        product_ids = [
            int(p["productId"]) for p in products if p.get("productId")
        ]
        fragments = [
            f"""
            p{pid}: product(entityId: {pid}) {{
              name
              defaultImage {{ url640wide: url(width: 640) }}
              prices {{ price {{ value currencyCode }} }}
            }}
        """ for pid in product_ids
        ]

        sf_headers = {
            "Content-Type":
            "application/json",
            "Authorization":
            f"Bearer {os.environ['BIGCOMMERCE_STOREFRONT_API_TOKEN']}"
        }

        res_sf = requests.post(
            STOREFRONT_GRAPHQL_ENDPOINT,
            json={"query": f"query {{ site {{ {' '.join(fragments)} }} }}"},
            headers=sf_headers)
        metadata = res_sf.json().get("data", {}).get("site", {})

        parts = []
        for p in products:
            pid = int(p["productId"])
            meta = metadata.get(f"p{pid}", {})
            name = meta.get("name", f"Product {pid}")
            qty = p.get("quantity")
            image = (meta.get("defaultImage") or {}).get("url640wide")
            price = (meta.get("prices") or {}).get("price", {})
            value = price.get("value", "??")
            currency = price.get("currencyCode", "")
            parts.append(Part(text=f"🛒 {qty}x {name} — {currency} {value}"))
            if image:
                parts.append(Part(text=f"🖼️ Image: {image}"))

        return Content(role="user", parts=parts)

    except Exception as e:
        return Content(role="user", parts=[Part(text=f"🔥 Error: {str(e)}")])


get_order_products_tool = FunctionTool(func=get_order_products)


def get_order_products_by_ids(order_ids: List[int],
                              tool_context: ToolContext) -> Content:
    token = tool_context.state.get("b2b_storefront_token")
    if not token:
        return Content(
            role="user",
            parts=[Part(text="❌ Missing B2B token in session state.")])

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    all_products = []
    storefront_ids = set()

    for oid in order_ids:
        query = """
        query GetOrderProducts($bcOrderId: Int!) {
          orderProducts(bcOrderId: $bcOrderId) {
            quantity
            productId
            variantId
          }
        }
        """
        res = requests.post(B2B_GRAPHQL_ENDPOINT,
                            json={
                                "query": query,
                                "variables": {
                                    "bcOrderId": oid
                                }
                            },
                            headers=headers)
        data = res.json().get("data", {}).get("orderProducts", [])
        for p in data:
            p["orderId"] = oid
            all_products.append(p)
            if p.get("productId"):
                storefront_ids.add(int(p["productId"]))

    # Fetch metadata from Storefront
    fragments = [
        f"""
        p{pid}: product(entityId: {pid}) {{
          name
          defaultImage {{ url640wide: url(width: 640) }}
          prices {{ price {{ value currencyCode }} }}
        }}
    """ for pid in storefront_ids
    ]

    res_sf = requests.post(
        STOREFRONT_GRAPHQL_ENDPOINT,
        json={"query": f"query {{ site {{ {' '.join(fragments)} }} }}"},
        headers={
            "Content-Type":
            "application/json",
            "Authorization":
            f"Bearer {os.environ['BIGCOMMERCE_STOREFRONT_API_TOKEN']}"
        })
    metadata = res_sf.json().get("data", {}).get("site", {})

    parts = []
    for p in all_products:
        pid = int(p["productId"])
        meta = metadata.get(f"p{pid}", {})
        name = meta.get("name", f"Product {pid}")
        qty = p.get("quantity")
        image = (meta.get("defaultImage") or {}).get("url640wide")
        price = (meta.get("prices") or {}).get("price", {})
        value = price.get("value", "??")
        currency = price.get("currencyCode", "")
        parts.append(
            Part(text=
                 f"📦 Order #{p['orderId']}: {qty}x {name} — {currency} {value}"
                 ))
        if image:
            parts.append(Part(text=f"🖼️ Image: {image}"))

    return Content(role="user",
                   parts=parts or [Part(text="No products found.")])


get_order_products_by_ids_tool = FunctionTool(func=get_order_products_by_ids)


def get_order_history(tool_context: CallbackContext) -> Dict:
    token = tool_context.state.get("b2b_storefront_token")
    if not token:
        return {
            "status": "error",
            "error_message": "Missing B2B token in state."
        }

    company_id = 2164075
    query = """
    query GetOrderHistory($companyId: Int!) {
      allOrders(
        companyIds: [$companyId]
        first: 10
        orderBy: "-bcOrderId"
      ) {
        edges {
          node {
            orderId
            createdAt
            totalIncTax
            currencyCode
            status
          }
        }
      }
    }
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        res = requests.post(B2B_GRAPHQL_ENDPOINT,
                            json={
                                "query": query,
                                "variables": {
                                    "companyId": company_id
                                }
                            },
                            headers=headers)
        data = res.json()
        orders = [
            edge["node"]
            for edge in data.get("data", {}).get("allOrders", {}).get(
                "edges", [])
        ]
        if not orders:
            return {
                "status": "not_found",
                "message": "No recent orders found."
            }

        for o in orders:
            try:
                ts = int(o["createdAt"])
                dt = datetime.utcfromtimestamp(ts)
                o["createdAt"] = format_datetime(dt)
            except Exception:
                pass  # Leave as-is if conversion fails

        tool_context.state["order_history"] = orders
        summary = "\n".join(
            f"- Order #{o['orderId']} on {o['createdAt']} • {o['currencyCode']} {o['totalIncTax']} • {o['status']}"
            for o in orders)
        return {
            "status": "success",
            "orders_count": len(orders),
            "summary": summary
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


read_order_history_tool = FunctionTool(func=get_order_history)


def read_order_history_from_state(tool_context: ToolContext) -> Content:
    orders = tool_context.state.get("order_history", [])
    if not orders:
        return Content(
            role="user",
            parts=[Part(text="⚠️ No order history found in session state.")])
    parts = [
        Part(
            text=
            f"🧾 Order #{o['orderId']} • {o['currencyCode']} {o['totalIncTax']} • {o['status']} • Placed on {o['createdAt']}"
        ) for o in orders
    ]
    return Content(role="user", parts=parts)


resolve_order_ids_tool = FunctionTool(func=read_order_history_from_state)


def resolve_order_ids_from_input(input_text: str,
                                 tool_context: ToolContext) -> Optional[dict]:
    history = tool_context.state.get("order_history", [])
    all_ids = [int(o["orderId"]) for o in history]  # most recent first
    input_text = input_text.lower()

    if "all" in input_text:
        return {"order_ids": all_ids}

    # ✅ Handles: "last 3", "last 5 orders", etc.
    match = re.search(r"last\s+(\d+)", input_text)
    if match:
        count = int(match.group(1))
        return {"order_ids": all_ids[:count]}

    # ✅ Handles: "orders 210-214" or "orders 210 to 214"
    match = re.search(r"orders?\s+(\d+)\s*[-to]+\s*(\d+)", input_text)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        return {"order_ids": [oid for oid in all_ids if start <= oid <= end]}

    # ✅ Fallback: grab numbers like "210", "212"
    ids = [int(num) for num in re.findall(r"\d+", input_text)]
    return {"order_ids": [oid for oid in all_ids if oid in ids]}


resolve_order_ids_tool = FunctionTool(func=resolve_order_ids_from_input)

__all__ = [
    "get_last_order_tool", "get_order_products_tool",
    "get_order_products_by_ids_tool", "read_order_history_tool",
    "resolve_order_ids_tool"
]
