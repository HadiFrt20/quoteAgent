from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.adk.memory import SearchMemoryResponse
from google.genai.types import Content, Part


def load_memory_wrapper(query: str, tool_context: ToolContext) -> Content:
    """Searches long-term memory and returns matching memory snippets."""
    try:
        result: SearchMemoryResponse = tool_context.search_memory(query)

        if not result or not result.results:
            return Content(
                role="user",
                parts=[
                    Part(text="🔍 No relevant memory found for this query.")
                ])

        lines = []
        for i, entry in enumerate(result.results, start=1):
            text = entry.text.strip() if entry.text else ""
            if text:
                lines.append(f"{i}. {text}")

        if not lines:
            return Content(
                role="user",
                parts=[Part(text="🧠 Memory search returned empty results.")])

        return Content(role="user", parts=[Part(text="\n".join(lines))])

    except Exception as e:
        return Content(role="user",
                       parts=[Part(text=f"❌ Memory search failed: {str(e)}")])


load_memory_tool = FunctionTool(func=load_memory_wrapper)
