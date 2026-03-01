from datetime import datetime
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from phi.agent import Agent
from phi.model.openai import OpenAIChat
from phi.tools.duckduckgo import DuckDuckGo
from phi.tools.newspaper4k import Newspaper4k

from dotenv import load_dotenv


def get_current_datetime() -> str:
    """Returns the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class _TextExtractor(HTMLParser):
    """Strips HTML tags and collects visible text."""
    SKIP_TAGS = {"script", "style", "head", "meta", "link", "noscript"}

    def __init__(self):
        super().__init__()
        self._text: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip = True

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self._text.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self._text)


def scrape_webpage(url: str) -> str:
    """Fetches and returns the visible text content of any HTTP or HTTPS webpage.

    Args:
        url: The full URL of the page to scrape (must start with http:// or https://).

    Returns:
        Extracted visible text from the page, or an error message if the request fails.
    """
    if not url.startswith(("http://", "https://")):
        return "Error: URL must start with http:// or https://"

    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            html = response.read().decode(charset, errors="replace")
        parser = _TextExtractor()
        parser.feed(html)
        text = parser.get_text()
        # Truncate to avoid overflowing the context window
        return text[:8000] if len(text) > 8000 else text
    except HTTPError as e:
        return f"HTTP error {e.code}: {e.reason}"
    except URLError as e:
        return f"URL error: {e.reason}"
    except Exception as e:
        return f"Failed to scrape page: {e}"

load_dotenv()

def create_websearch_agent():
    """Creates a single conversational agent."""
    agent = Agent(
        name="Jarvis",
        model=OpenAIChat(id="gpt-4o"),
        description="You are a research assistant that searches the web for information",
        instructions=[
            "Always search for the most recent information.",
            "Include sources in your responses.",
            "Summarize findings clearly.",
            "Use the get_current_datetime tool to get today's date and time when the query involves current events, recent news, or time-sensitive information.",
            "Use the Newspaper4k tool to scrape and read the full content of a URL when deeper article details are needed beyond search snippets.",
            "Use the scrape_webpage tool to fetch and read any HTTP or HTTPS URL when Newspaper4k is insufficient or when raw page text is needed.",
        ],
        show_tool_calls=True,
        markdown=True,
        debug_mode=False, 
        tools=[DuckDuckGo(), Newspaper4k(), get_current_datetime, scrape_webpage]
    )
    return agent

if __name__ == "__main__":
    agent = create_websearch_agent()
    agent.print_response("what is the value of pi", stream=True)