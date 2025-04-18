from google.adk.agents.callback_context import CallbackContext
from google.genai.types import Content, Part
from typing import Optional
from quote_agent.tools.orders import get_order_history
from quote_agent.tools.catalog import (preload_customer_catalog,
                                       ingest_catalog_to_memory)
import requests
import os

B2B_TOKEN_API = "https://api-b2b.bigcommerce.com/api/io/auth/customers/storefront"
AUTH_TOKEN = os.environ["B2B_REST_API_TOKEN"]
CUSTOMER_ID = 25
CHANNEL_ID = 1


def preload_agent_context(
        callback_context: CallbackContext) -> Optional[Content]:
    state = callback_context.state

    # Load B2B Storefront token
    print("🔑 Fetching B2B Storefront token...")
    try:
        res = requests.post(
            B2B_TOKEN_API,
            json={
                "customerId": CUSTOMER_ID,
                "channelId": CHANNEL_ID
            },
            headers={
                "Content-Type": "application/json",
                "authToken": AUTH_TOKEN
            },
        )

        print("📥 Token response:", res.status_code)
        print(res.text)

        res.raise_for_status()
        token = res.json().get("data", {}).get("token", [None])[0]
        if token:
            state["b2b_storefront_token"] = token
            print("✅ Token saved.")
        else:
            state["b2b_storefront_token"] = None
            return Content(role="user",
                           parts=[Part(text="⚠️ Token fetch failed.")])
    except Exception as e:
        print(f"❌ Token fetch error: {e}")
        state["b2b_storefront_token"] = None
        return Content(role="user",
                       parts=[Part(text="❌ Failed to fetch token.")])

    # Load order history
    if "order_history" not in state:
        try:
            get_order_history(callback_context)
            print("✅ Order history loaded.")
        except Exception as e:
            print(f"⚠️ Failed to load order history: {e}")

    # Preload catalog into session state
    try:
        preload_customer_catalog(callback_context)
    except Exception as e:
        print(f"⚠️ Failed to preload catalog into session state: {e}")

    # Ingest into memory — fallback to session-derived IDs
    try:
        session = getattr(callback_context, "session", None)
        if session:
            app_name = session.app_name
            user_id = session.user_id
            session_id = session.id
            ingest_catalog_to_memory(app_name, user_id, session_id)
        else:
            print(
                "⚠️ Session not found in callback_context. Skipping memory ingest."
            )
    except Exception as e:
        print(f"⚠️ Failed to ingest catalog into memory: {e}")

    return None
