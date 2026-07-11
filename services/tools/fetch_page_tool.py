import httpx
from bs4 import BeautifulSoup
from services.tools.base_tool import Tool

class FetchPageTool(Tool):
    name = "fetch_page"
    description = "Fetch the text content of a web page. Input: a URL string."

    def run(self, url):
        response = httpx.get(url, timeout=10, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # Remove script/style tags entirely

        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

        return text[:5000]