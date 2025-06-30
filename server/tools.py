from mcp.server.fastmcp import FastMCP
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser
from langchain.agents import initialize_agent, AgentType
from langchain.prompts import MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
import asyncio

mcp = FastMCP(name="PlaywrightAgent")


# 1) Launch browser and toolkit (sync version)
async def init_browser():
    return await create_async_playwright_browser()

async_browser = asyncio.run(init_browser())
toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
tools = toolkit.get_tools()

# 2) LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

chat_history = MessagesPlaceholder(variable_name="chat_history")
memory = ConversationBufferMemory(
    memory_key="chat_history", return_messages=True)

# 3) Build agent once
agent = initialize_agent(
    agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    tools=tools,
    llm=llm,
    verbose=True,
    max_iterations=5,
    memory=memory,
    agent_kwargs={
        "memory_prompts": [chat_history],
        "input_variables": ["input", "agent_scratchpad", "chat_history"]
    }
)

@mcp.tool()
def search_with_browser(input: str) -> str:
    """
    Use browser automation tools to search the web and return summarized insights.
    
    Args:
        input: Natural-language search query.
    
    Returns:
        A text-based answer based solely on browser navigation result.
    """
    
    return agent.run(input)

# 5. Launch the server
if __name__ == "__main__":
    # Expose over HTTP for client use
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
