from google.adk.tools import ToolContext, FunctionTool
import requests
import os
import json

B2B_QUOTE_API = "https://api-b2b.bigcommerce.com/api/v3/io/rfq"
AUTH_TOKEN = os.environ["B2B_REST_API_TOKEN"]
STORE_HASH = os.environ["BIGCOMMERCE_STORE_HASH"]


def create_quote_request_tool_func(product_id: int, quantity: int, note: str,
                                   tool_context: ToolContext) -> dict:
    """
    Creates a quote request using BigCommerce's B2B REST API with catalog-backed data.
    """
    catalog = tool_context.state.get("catalog", [])
    product = next((p for p in catalog if p["id"] == product_id), None)

    if not product:
        return {
            "status": "error",
            "message": f"Product {product_id} not found in catalog."
        }
    if not product.get("price"):
        return {
            "status": "error",
            "message": f"Product {product_id} is missing price information."
        }

    # Extract product data
    base_price = float(product["price"])
    discount_percent = 0.20
    discount_amount = round(base_price * discount_percent, 2)
    offered_price = round(base_price - discount_amount, 2)
    subtotal = round(base_price * quantity, 2)
    grand_total = round(offered_price * quantity, 2)
    total_discount = round(subtotal - grand_total, 2)

    payload = {
        "notes":
        note,
        "legalTerms":
        "Quote valid for 30 days. Net 30 terms. FOB shipping point.",
        "grandTotal":
        grand_total,
        "discount":
        total_discount,
        "subtotal":
        subtotal,
        "referenceNumber":
        "agent_quote_ref",
        "userEmail":
        "salestaff_1@senatorgroup.com",
        "expiredAt":
        "12/31/2025",
        "quoteTitle":
        f"Agent Quote: {product['name']}",
        "contactInfo": {
            "name": "Admin MKM",
            "email": "admin@glfstore.co.uk",
            "companyName": "MKM",
            "phoneNumber": "0123456789"
        },
        "companyId":
        2164075,
        "currency": {
            "token": "£",
            "location": "left",
            "currencyCode": "GBP",
            "decimalToken": ".",
            "decimalPlaces": 2,
            "thousandsToken": ","
        },
        "storeHash":
        STORE_HASH,
        "productList": [{
            "sku": product.get("sku"),
            "productId": product_id,
            "quantity": quantity,
            "basePrice": str(base_price),
            "discount": str(discount_amount),
            "offeredPrice": str(offered_price),
            "variantId": product_id,
            "imageUrl": product.get("image"),
            "productName": product["name"],
            "options": []
        }],
        "channelId":
        1,
        "fileList": [],
        "extraFields": [],
        "recipients": [],
        "allowCheckout":
        False
    }

    headers = {"Content-Type": "application/json", "authToken": AUTH_TOKEN}

    response = None
    try:
        print("📤 Sending quote creation payload:")
        print(json.dumps(payload, indent=2))

        response = requests.post(B2B_QUOTE_API, headers=headers, json=payload)
        print("📥 Quote API response:")
        print(response.status_code, response.text)
        response.raise_for_status()
        return {"status": "success", "response": response.json()}

    except requests.RequestException as e:
        return {
            "status": "error",
            "message": str(e),
            "details": response.text if response else "No response returned"
        }


create_quote_request_tool = FunctionTool(func=create_quote_request_tool_func)
__all__ = ["create_quote_request_tool"]
