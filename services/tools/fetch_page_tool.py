import httpx
from services.tools.base_tool import Tool

class FetchPageTool(Tool):
    name = "fetch_page"
    description = "Fetch the text content of a web page. Input: a URL string."

    def run(self, url):
        response = httpx.get(url, timeout=10, follow_redirects=True)
        response.raise_for_status()
        return response.text[:5000]