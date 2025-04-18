from google.adk.tools import ToolContext, FunctionTool
from typing import Optional
import requests
import os
import json

STORE_HASH = os.environ["BIGCOMMERCE_STORE_HASH"]
API_TOKEN = os.environ["BIGCOMMERCE_REST_API_TOKEN"]
ORDERS_API = f"https://api.bigcommerce.com/stores/{STORE_HASH}/v2/orders"
CUSTOMER_API = f"https://api.bigcommerce.com/stores/{STORE_HASH}/v2/customers"


def _calculate_discount_value_from_percentage(
        product_id: int, quantity: int, discount_percent: float,
        tool_context: ToolContext) -> float:
    """
    Looks up product price from catalog and computes flat discount amount
    """
    catalog = tool_context.state.get("catalog", [])
    product = next((p for p in catalog if p["id"] == product_id), None)

    if not product:
        raise ValueError(f"Product {product_id} not found in catalog.")

    price = product.get("price")
    if price is None:
        raise ValueError(f"Product {product_id} missing price in catalog.")

    subtotal = float(price) * quantity
    discount_value = round(subtotal * (discount_percent / 100), 2)
    return discount_value


def create_discounted_order_tool_func(
    product_id: int,
    quantity: int,
    discount_percent: float,
    tool_context: ToolContext,
) -> dict:
    """
    Creates a discounted BigCommerce order for a single product and customer (hardcoded for now).
    Includes full logging and error handling.
    """

    headers = {
        "X-Auth-Token": API_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    customer_id = 25  # 🔒 Replace with dynamic lookup if needed

    # Step 1: Fetch address
    try:
        addr_url = f"{CUSTOMER_API}/{customer_id}/addresses"
        print(f"📬 Fetching billing address from: {addr_url}")
        addr_res = requests.get(addr_url, headers=headers)
        print(f"🔎 Address response status: {addr_res.status_code}")
        print(f"📥 Address response:\n{addr_res.text}")
        addr_res.raise_for_status()

        addresses = addr_res.json()
        if not addresses:
            return {
                "status": "error",
                "message": f"No address found for customer {customer_id}"
            }

        allowed_keys = {
            "first_name", "last_name", "street_1", "street_2", "city", "state",
            "zip", "country", "country_iso2", "email", "company"
        }
        billing_address = {
            k: v
            for k, v in addresses[0].items() if k in allowed_keys
        }
        print("✅ Using billing address:")
        print(json.dumps(billing_address, indent=2))

    except Exception as e:
        print("❌ Failed to fetch billing address.")
        return {
            "status": "error",
            "message": f"Address fetch failed: {str(e)}"
        }

    # Step 2: Compute discount value
    try:
        discount_amount = _calculate_discount_value_from_percentage(
            product_id, quantity, discount_percent, tool_context)
        print(
            f"💸 Calculated discount ({discount_percent}%): £{discount_amount}")
    except Exception as e:
        return {"status": "error", "message": str(e)}

    # Step 3: Build order payload
    payload = {
        "status_id": 2,
        "channel_id": 1,
        "customer_id": customer_id,
        "billing_address": billing_address,
        "products": [{
            "product_id": product_id,
            "quantity": quantity
        }],
        "discount_amount": str(discount_amount),
        "default_currency_code": "GBP"
    }

    print("📤 Sending order payload:")
    print(json.dumps(payload, indent=2))

    # Step 4: POST to create order
    order_res: Optional[requests.Response] = None
    try:
        order_res = requests.post(ORDERS_API, json=payload, headers=headers)
        print(f"🔁 Order API status: {order_res.status_code}")
        print("📥 Order response text:")
        print(order_res.text)

        order_res.raise_for_status()
        order = order_res.json()
        tool_context.state["last_order_created"] = order

        print(f"✅ Order created successfully: #{order.get('id')}")
        return {
            "status":
            "success",
            "order_id":
            order.get("id"),
            "total":
            order.get("total_inc_tax"),
            "label":
            f"AI Negotiation Discount ({discount_percent:.0f}%)",
            "link":
            f"https://store-{STORE_HASH}.mybigcommerce.com/manage/orders/{order.get('id')}"
        }

    except requests.RequestException as e:
        print("❌ Order creation failed!")
        if order_res is not None:
            print(f"❌ Error status: {order_res.status_code}")
            print(f"❌ Error body:\n{order_res.text}")
            try:
                return {
                    "status": "error",
                    "message": str(e),
                    "details": order_res.json()
                }
            except Exception:
                return {
                    "status": "error",
                    "message": str(e),
                    "raw_response": order_res.text
                }
        else:
            return {
                "status": "error",
                "message": str(e),
                "details": "No response returned"
            }


create_discounted_order_tool = FunctionTool(
    func=create_discounted_order_tool_func)

__all__ = ["create_discounted_order_tool"]
