from mcp.server.fastmcp import FastMCP
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_sync_playwright_browser
from langchain.agents import initialize_agent, AgentType
from langchain.prompts import MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
import hashlib
import time
import functools
from dotenv import load_dotenv
load_dotenv()
import os
os.environ["OPENAI_API_KEY"]=os.getenv("OPENAI_API_KEY")

# Basic in-memory cache
_CACHE = {}

def cache_with_expiry(expiry_seconds=300):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = hashlib.sha256(str((func.__name__, args, kwargs)).encode()).hexdigest()
            if key in _CACHE:
                cached_time, result = _CACHE[key]
                if time.time() - cached_time < expiry_seconds:
                    return result
            result = func(*args, **kwargs)
            _CACHE[key] = (time.time(), result)
            return result
        return wrapper
    return decorator

class TaxWebScraperAgent:
    def __init__(self, model_name="gpt-4o-mini", temperature=0):
        self.llm = ChatOpenAI(model=model_name, temperature=temperature)
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.chat_history = MessagesPlaceholder(variable_name="chat_history")

        # Setup browser and tools
        self.browser = create_sync_playwright_browser()
        self.toolkit = PlayWrightBrowserToolkit.from_browser(sync_browser=self.browser)
        self.browser_tools = self.toolkit.get_tools()

        self.agent = initialize_agent(
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            tools=self.browser_tools,
            llm=self.llm,
            verbose=True,
            memory=self.memory,
            agent_kwargs={
                "memory_prompts": [self.chat_history],
                "input_variables": ["input", "agent_scratchpad", "chat_history"]
            }
        )

    @cache_with_expiry(expiry_seconds=600)
    def run_browser_agent(self, query: str, max_retries: int = 3) -> str:
        """
        Run the browser agent with retry and caching support.
        """
        for attempt in range(max_retries):
            try:
                result = self.agent.run(query)
                return result.strip()
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"Error after {max_retries} attempts: {str(e)}"
                time.sleep(2 ** attempt)

# Initialize MCP
mcp = FastMCP(name="PlaywrightTaxScraper")
scraper_agent = TaxWebScraperAgent()

@mcp.tool()
def browser_search(input: str) -> str:
    """
    Navigate the internet and return structured insights from the search.
    Example: "Search for latest IRS rules on child tax credit."
    """
    return scraper_agent.run_browser_agent(input)

@mcp.tool()
def irs_topic_summary(topic: str) -> str:
    """
    Visit IRS.gov and summarize official details about a given topic.
    Example: "self-employment tax deduction"
    """
    query = f"Go to https://www.irs.gov and find official details about: {topic}. Summarize all relevant pages."
    return scraper_agent.run_browser_agent(query)

@mcp.tool()
def irs_direct_page_summary(subpage_path: str) -> str:
    """
    Navigate directly to a specific IRS.gov subpage and summarize its contents.
    Example: "businesses/small-businesses-self-employed/self-employment-tax"
    """
    url = f"https://www.irs.gov/{subpage_path.strip('/')}"
    query = f"Navigate to {url} and summarize the page in detail."
    return scraper_agent.run_browser_agent(query)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
