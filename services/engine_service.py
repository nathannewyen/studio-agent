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

def test_call(question):
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text

def run_agent(question, max_steps = 10):
    messages = [{"role": "user", "content": question}]
    step = 0

    while step < max_steps:
        response = client.messages.create(
            model = "claude-haiku-4-5",
            max_tokens = 1000,
            tools = tools,
            messages = messages
        )
    
        if response.stop_reason == "tool_use":
            # Step 1: save Claude's response to history
            messages.append({"role": "assistant", "content": response.content})

            # Step 2: find what tool Claude wants + its input
            tool_use = next(block for block in response.content if block.type == "tool_use")
            tool_name = tool_use.name
            tool_input = tool_use.input

            # Step 3: run the actual tool
            search_tool = TOOL_REGISTRY[tool_name]
            result = tools.run(**tool_input)

            # Step 4: send the result back to Claude
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": str(result),
                }]
            })
        else:
            break
        step += 1
    return response.content[0].text