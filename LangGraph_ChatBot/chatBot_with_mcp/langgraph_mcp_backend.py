from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import  BaseMessage,HumanMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from dotenv import load_dotenv
import aiosqlite
import httpx
import math

load_dotenv()
DB_PATH = "ChatBot.db"
_CACHED_TOOLS = None
_GRAPH_BUILDER = None

llm=ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")

search_tool = TavilySearch(max_results=2)

@tool("calculator")
def calculator(expression: str) -> str:
    """
    A simple calculator tool for evaluating math expressions safely.
    Supports +, -, *, /, **, %, parentheses, and math functions.
    
    Example:
    >>> calculator("2 + 3 * (4 ** 2)")
    50
    """
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
    
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"
    
@tool
async def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=4LRHDYMCFI2REVKP"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return r.json()

def fix_mcp_tool(tool):
    tool.handle_tool_error = True 

    return tool

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

async def get_tools_and_builder():
    global _CACHED_TOOLS, _GRAPH_BUILDER

    if _CACHED_TOOLS is None:
        try:
            mcp_client= MultiServerMCPClient({
                "Expense Tracker": {
                    "transport": "streamable_http",
                    "url": "https://tender-chocolate-mastodon.fastmcp.app/mcp"
                }
            })
            raw_mcp_tools  = await mcp_client.get_tools()
            mcp_tools = [fix_mcp_tool(t) for t in raw_mcp_tools]
            print(f"Loaded {len(mcp_tools)} MCP tools.")
        except Exception as e:
            print(f"MCP Connection failed: {e}")
            mcp_tools = []
        _CACHED_TOOLS = [search_tool, get_stock_price, calculator] + mcp_tools

    if _GRAPH_BUILDER is None:
        llm_with_tools = llm.bind_tools(_CACHED_TOOLS)

        async def chat_node(state: ChatState):
            return {"messages": [await llm_with_tools.ainvoke(state['messages'])]}

        tool_node = ToolNode(_CACHED_TOOLS)

        workflow = StateGraph(ChatState)
        workflow.add_node("chat_node", chat_node)
        workflow.add_node("tools", tool_node)
        workflow.add_edge(START, "chat_node")
        workflow.add_conditional_edges("chat_node", tools_condition)
        workflow.add_edge("tools", "chat_node")
        
        _GRAPH_BUILDER = workflow

    return _CACHED_TOOLS, _GRAPH_BUILDER

async def stream_chat(thread_id: str, user_input: str):
    tools, builder = await get_tools_and_builder()

    async with aiosqlite.connect(DB_PATH) as conn:
        checkpointer = AsyncSqliteSaver(conn)
        
        app = builder.compile(checkpointer=checkpointer)
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # 4. Stream
        async for event in app.astream(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
            stream_mode="messages"
        ):
            yield event

async def init_db():
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                thread_id TEXT PRIMARY KEY,
                name TEXT DEFAULT 'New Chat'
            )
        """)
        await conn.commit()

async def get_all_threads_db():
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute("SELECT thread_id, name FROM threads") as cursor:
            rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}

async def save_thread_db(thread_id: str, name: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO threads (thread_id, name) VALUES (?, ?)",
            (thread_id, name)
        )
        await conn.commit()

async def delete_thread_db(thread_id: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        try:
            await conn.execute("DELETE FROM threads WHERE thread_id = ?", (thread_id,))
            await conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        except aiosqlite.OperationalError:
            pass 
        await conn.commit()

async def clear_db():
    async with aiosqlite.connect(DB_PATH) as conn:
        try:
            await conn.execute("DELETE FROM threads")
            await conn.execute("DELETE FROM checkpoints")
        except aiosqlite.OperationalError:
            pass
        await conn.commit()

async def get_history(thread_id: str):
    tools, builder = await get_tools_and_builder()
    async with aiosqlite.connect(DB_PATH) as conn:
        checkpointer = AsyncSqliteSaver(conn)
        app = builder.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state = await app.aget_state(config)
            return state.values.get("messages", [])
        except:
            return []
        