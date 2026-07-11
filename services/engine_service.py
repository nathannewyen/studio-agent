import os
from anthropic import Anthropic

from services.tools.web_search_tool import WebSearchTool
from services.tools.fetch_page_tool import FetchPageTool

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

TOOL_REGISTRY = {
    "web_search": WebSearchTool(),
    "fetch_page": FetchPageTool(),
}

tools = [
    {
        "name": "web_search",
        "description": "Search the web for current information.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }
    },
    {
        "name": "fetch_page",
        "description": "Fetch the full text content of a web page by URL.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    }
]

def run_agent(question, max_steps = 10):
    messages = [{"role": "user", "content": question}]
    step = 0
    completed = False

    while step < max_steps:
        response = client.messages.create(
            model = "claude-haiku-4-5",
            max_tokens = 5000,
            tools = tools,
            messages = messages
        )
    
        if response.stop_reason == "tool_use":
            # Save Claude's response to history
            messages.append({"role": "assistant", "content": response.content})

            # findAll tool_use blocks, not just the first
            tool_uses = [b for b in response.content if b.type == "tool_use"]

            tool_results = []
            # Find what tool Claude wants + its input
            for i, tool_use in enumerate(tool_uses):
                tool_name = tool_use.name
                tool_input = tool_use.input

                print(f"Step {step}.{i}: Claude called {tool_name} with {tool_input}")

                # Run the actual tool
                tool = TOOL_REGISTRY[tool_name]
                try:
                    result = tool.run(**tool_input)
                    is_error = False
                except Exception as e:
                    result = f"Tool failed: {e}"
                    is_error = True
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": str(result),
                    "is_error": is_error,
                })

            # Send the result back to Claude in one message
            messages.append({"role": "user", "content": tool_results})
        elif response.stop_reason == "end_turn":
            completed = True
            break
        elif response.stop_reason == "max_tokens":
            return {
                "answer": None,
                "message": "Sorry, that's a big question. I'm on a budget and my token allowance ran out mid-thought 🥹",
                "truncated": True,
            }
        else:
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")
        step += 1

    if not completed:
        return {
            "answer": None,
            "truncated": False,
            "message": " couldn't finish that one, ran out of steps while researching 😞."
        }

    return {
        "answer": response.content[0].text,
        "truncated": False,
    }