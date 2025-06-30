import chainlit as cl
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain.prompts import MessagesPlaceholder
from mcp.client import MultiServerMCPClient
import os

# === MCP Client Setup ===
mcp = MultiServerMCPClient({
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
all_tools = mcp.get_tools()

# === Memory ===
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
chat_history_placeholder = MessagesPlaceholder(variable_name="chat_history")

# === LLM ===
llm = ChatOpenAI(model="gpt-4o", temperature=0, streaming=True)

# === Agent ===
prompt = create_react_agent(llm=llm, tools=all_tools, prompt_kwargs={
    "memory_prompts": [chat_history_placeholder],
    "input_variables": ["input", "agent_scratchpad", "chat_history"]
}).prompt

agent_executor = AgentExecutor.from_agent_and_tools(
    agent=create_react_agent(llm=llm, tools=all_tools, prompt=prompt),
    tools=all_tools,
    memory=memory,
    verbose=True,
    handle_parsing_errors=True,
    return_intermediate_steps=False
)

# === Chainlit Hooks ===
@cl.on_chat_start
def start():
    cl.user_session.set("agent", agent_executor)

@cl.on_message
def handle_message(msg: cl.Message):
    agent = cl.user_session.get("agent")
    response = ""
    for chunk in agent.stream(msg.content):
        response += chunk.get("output", "")
        yield cl.Message(content=response)

@cl.on_chat_end
def end():
    mcp.close()
