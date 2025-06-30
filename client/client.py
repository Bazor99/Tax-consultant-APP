import os
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()
os.environ["OPENAI_API_KEY"]=os.getenv("OPENAI_API_KEY")

async def main():
    client = MultiServerMCPClient({
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem",
                    "C:\\Users\\Zbook\\Desktop\\mcp-chainlit"],
            "transport": "stdio"
        },
        "slack": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-slack"],
            "transport": "stdio",
            "env": {
                "SLACK_BOT_TOKEN": os.getenv("SLACK_BOT_TOKEN"),
                "SLACK_TEAM_ID": os.getenv("SLACK_TEAM_ID"),
            }
        },
        "stripe": {
            "command": "npx",
            "args": ["-y", "@stripe/mcp", "--tools=all", "--api-key", os.getenv("STRIPE_SECRET_KEY")],
            "transport": "stdio"
        },
        "tax_scraper": {
            "url": "http://localhost:8000/mcp/",
            "transport": "streamable_http"
        }
    })

    tools = await client.get_tools()  # loads tools from all servers
    print("🚀 Loaded tools:", [tool.name for tool in tools])

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    agent = create_react_agent(llm=llm, tools=tools)

    print("Type questions (exit to stop):")
    while True:
        u = input("> ")
        if u.strip().lower() in ("exit", "quit"):
            break
        resp = await agent.ainvoke({"messages": [{"role": "user", "content": u}]})
        print(resp["messages"][-1].content, "\n")

    await client.aclose()

if __name__ == "__main__":
    assert os.getenv("OPENAI_API_KEY"), "Set OPENAI_API_KEY"
    asyncio.run(main())
