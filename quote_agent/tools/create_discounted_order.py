from typing import List
from pydantic import BaseModel
from google.adk.tools import ToolContext, FunctionTool
import requests
import os
import json

STORE_HASH = os.environ["BIGCOMMERCE_STORE_HASH"]
API_TOKEN = os.environ["BIGCOMMERCE_REST_API_TOKEN"]
ORDERS_API = f"https://api.bigcommerce.com/stores/{STORE_HASH}/v2/orders"
CUSTOMER_API = f"https://api.bigcommerce.com/stores/{STORE_HASH}/v2/customers"


class ProductItem(BaseModel):
    product_id: int
    quantity: int


class MultiOrderArgs(BaseModel):
    products: List[ProductItem]
    discount_percent: float


def _calculate_discount(products: List[ProductItem], discount_percent: float,
                        tool_context: ToolContext) -> float:
    catalog = tool_context.state.get("catalog", [])
    total = 0.0
    for item in products:
        product = next((p for p in catalog if p["id"] == item.product_id),
                       None)
        if not product or product.get("price") is None:
            raise ValueError(f"Missing price for product {item.product_id}")
        total += float(product["price"]) * item.quantity
    return round(total * (discount_percent / 100), 2)


def create_multi_item_discounted_order_afc(products: List[ProductItem],
                                           discount_percent: float,
                                           tool_context: ToolContext) -> dict:
    headers = {
        "X-Auth-Token": API_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    customer_id = 25

    try:
        addr_res = requests.get(f"{CUSTOMER_API}/{customer_id}/addresses",
                                headers=headers)
        addr_res.raise_for_status()
        addresses = addr_res.json()
        if not addresses:
            return {"status": "error", "message": "No billing address found"}

        billing_address = {
            k: v
            for k, v in addresses[0].items() if k in {
                "first_name", "last_name", "company", "street_1", "street_2",
                "city", "state", "zip", "country", "country_iso2"
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"Address fetch failed: {e}"}

    try:
        discount_amount = _calculate_discount(products, discount_percent,
                                              tool_context)
    except Exception as e:
        return {"status": "error", "message": f"Discount error: {e}"}

    payload = {
        "status_id": 2,
        "channel_id": 1,
        "customer_id": customer_id,
        "billing_address": billing_address,
        "products": [item.dict() for item in products],
        "discount_amount": str(discount_amount),
        "default_currency_code": "GBP"
    }

    print("📤 Payload:\n", json.dumps(payload, indent=2))
    res = None
    try:
        res = requests.post(ORDERS_API, headers=headers, json=payload)
        res.raise_for_status()
        order = res.json()
        tool_context.state["last_order_created"] = order
        return {
            "status": "success",
            "order_id": order["id"],
            "total": order.get("total_inc_tax"),
            "label": f"AI Negotiation Discount ({discount_percent:.0f}%)"
        }
    except requests.RequestException as e:
        return {
            "status": "error",
            "message": str(e),
            "raw_response": res.text if res else "No response"
        }


def create_multi_item_discounted_order_wrapper(
        products: List[dict], discount_percent: float,
        tool_context: ToolContext) -> dict:
    try:
        parsed = MultiOrderArgs(products=[ProductItem(**p) for p in products],
                                discount_percent=discount_percent)
    except Exception as e:
        return {"status": "error", "message": f"Invalid input: {e}"}

    return create_multi_item_discounted_order_afc(
        products=parsed.products,
        discount_percent=parsed.discount_percent,
        tool_context=tool_context,
    )


create_multi_item_discounted_order_tool = FunctionTool(
    func=create_multi_item_discounted_order_wrapper)

__all__ = ["create_multi_item_discounted_order_tool"]
