from typing import List
from pydantic import BaseModel
from google.adk.tools import ToolContext, FunctionTool
import requests
import os
import json

B2B_QUOTE_API = "https://api-b2b.bigcommerce.com/api/v3/io/rfq"
AUTH_TOKEN = os.environ["B2B_REST_API_TOKEN"]
STORE_HASH = os.environ["BIGCOMMERCE_STORE_HASH"]


class ProductInput(BaseModel):
    product_id: int
    quantity: int


class CombinedQuoteArgs(BaseModel):
    products: List[ProductInput]
    note: str


def create_combined_quote_request_tool_func(products: List[dict], note: str,
                                            tool_context: ToolContext) -> dict:
    # manually create model
    try:
        args = CombinedQuoteArgs(
            products=[ProductInput(**p) for p in products], note=note)
    except Exception as e:
        return {"status": "error", "message": f"Invalid input format: {e}"}

    catalog = tool_context.state.get("catalog", [])
    product_list = []
    subtotal = 0.0
    total_discount = 0.0

    for entry in args.products:
        product_id = entry.product_id
        quantity = entry.quantity
        product = next((p for p in catalog if p["id"] == product_id), None)

        if not product:
            return {
                "status": "error",
                "message": f"Product {product_id} not found in catalog."
            }
        if not product.get("price"):
            return {
                "status": "error",
                "message": f"Product {product_id} missing price."
            }

        base_price = float(product["price"])
        discount_percent = 0.20
        discount_amount = round(base_price * discount_percent, 2)
        offered_price = round(base_price - discount_amount, 2)
        line_subtotal = base_price * quantity
        line_discount = discount_amount * quantity

        subtotal += line_subtotal
        total_discount += line_discount

        product_list.append({
            "productId": product_id,
            "variantId": product_id,
            "quantity": quantity,
            "basePrice": str(base_price),
            "discount": str(discount_amount),
            "offeredPrice": str(offered_price),
            "sku": product.get("sku"),
            "productName": product.get("name"),
            "imageUrl": product.get("image"),
            "options": []
        })

    grand_total = round(subtotal - total_discount, 2)

    payload = {
        "notes": args.note,
        "quoteTitle": "Agent Quote: Bundle Request",
        "referenceNumber": "bundle_quote_request",
        "expiredAt": "12/31/2025",
        "legalTerms":
        "Quote valid for 30 days. Net 30 terms. FOB shipping point.",
        "subtotal": round(subtotal, 2),
        "discount": round(total_discount, 2),
        "grandTotal": grand_total,
        "userEmail": "salestaff_1@senatorgroup.com",
        "companyId": 2164075,
        "storeHash": STORE_HASH,
        "currency": {
            "token": "£",
            "location": "left",
            "currencyCode": "GBP",
            "decimalToken": ".",
            "decimalPlaces": 2,
            "thousandsToken": ","
        },
        "contactInfo": {
            "name": "Sophie Randle",
            "email": "admin@mkmechanical.co.uk",
            "companyName": "MK Mechanical Solutions",
            "phoneNumber": "0123456789"
        },
        "channelId": 1,
        "productList": product_list,
        "fileList": [],
        "extraFields": [],
        "recipients": [],
        "allowCheckout": False
    }

    headers = {"Content-Type": "application/json", "authToken": AUTH_TOKEN}
    response = None
    try:
        print("📤 Sending combined quote creation payload:")
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


create_combined_quote_request_tool = FunctionTool(
    func=create_combined_quote_request_tool_func)
