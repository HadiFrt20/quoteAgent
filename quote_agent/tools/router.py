from google.adk.tools import agent_tool
from quote_agent.agents.orders import order_agent
from quote_agent.agents.bundles import bundle_agent
from quote_agent.agents.negotiation import negotiation_agent

order_agent_tool = agent_tool.AgentTool(agent=order_agent)
bundle_agent_tool = agent_tool.AgentTool(agent=bundle_agent)
negotiation_agent_tool = agent_tool.AgentTool(agent=negotiation_agent)

__all__ = ["order_agent_tool", "bundle_agent_tool", "negotiation_agent_tool"]
