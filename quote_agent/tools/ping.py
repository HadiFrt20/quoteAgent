def ping() -> dict:
    """Responds with pong for agent heartbeat check.

  Returns:
      dict: {"status": "success", "message": "pong"}
  """
    return {"status": "success", "message": "pong"}
