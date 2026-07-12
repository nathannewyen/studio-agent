from langchain_core.tools import tool

from services.tools.web_search_tool import WebSearchTool
from services.tools.fetch_page_tool import FetchPageTool

_web_search = WebSearchTool()
_fetch_page = FetchPageTool()


@tool
def web_search(query: str) -> list:
    """Search the web for current information."""
    return _web_search.run(query=query)


@tool
def fetch_page(url: str) -> str:
    """Fetch the full text content of a web page by URL."""
    return _fetch_page.run(url=url)


LC_TOOL_REGISTRY = {
    "web_search": web_search,
    "fetch_page": fetch_page,
}

TOOL_CATALOG = [
    {
        "name": "web_search",
        "description": "Search the web for current information.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "fetch_page",
        "description": "Fetch the full text content of a web page by URL.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
]
