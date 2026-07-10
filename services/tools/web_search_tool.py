import os
from tavily import TavilyClient
from services.tools.base_tool import Tool

class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web for current information. Input: a search query string."

    def __init__(self):
        self.tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    def run(self, query):
        response = self.tavily_client.search(query=query, max_results=3)
        # return just the useful bits: title, url, content snippet
        results = [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in response["results"]
        ]
        return results