import os


class Config:
  # BigCommerce
  DISCOUNT_THRESHOLD = 0.10  # 10% discount threshold for quote negotiation
  DEFAULT_CURRENCY = "GBP"
  store_hash = os.environ["BIGCOMMERCE_STORE_HASH"]
  api_token = os.environ["BIGCOMMERCE_API_TOKEN"]
  base_url = f"https://api.bigcommerce.com/stores/{store_hash}/v3"
  headers = {
      "X-Auth-Token": api_token,
      "Accept": "application/json",
      "Content-Type": "application/json"
  }

  # Gemini
  google_api_key = os.environ["GOOGLE_API_KEY"]
  use_vertex_ai = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI",
                                 "False").lower() == "true"


# BigCommerce config and credentials loader
