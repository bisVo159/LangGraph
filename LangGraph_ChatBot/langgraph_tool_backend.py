from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import  BaseMessage,HumanMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from dotenv import load_dotenv
import sqlite3
import requests
import math

load_dotenv()

llm=ChatGoogleGenerativeAI(model="gemini-2.5-flash")

search_tool = TavilySearch(max_results=2)

@tool("calculator", return_direct=True)
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
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=4LRHDYMCFI2REVKP"
    r = requests.get(url)
    return r.json()

tools = [search_tool, get_stock_price, calculator]
llm_with_tools = llm.bind_tools(tools)

tool_node = ToolNode(tools)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state: ChatState):
    messages = state['messages']
    response = llm_with_tools.invoke(messages)
    
    return {"messages":[response]}

conn=sqlite3.connect(database='ChatBot.db',check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

graph=StateGraph(ChatState)
graph.add_node("chat_node",chat_node)
graph.add_node("tools",tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node",tools_condition)
graph.add_edge("tools", "chat_node")

chatbot=graph.compile(checkpointer=checkpointer)



# DB interaction FUnctions
def retrieve_state_threads():
    all_threads=set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
        
    return list(all_threads)

def save_thread(thread_id: str, name: str = "New Chat"):
    conn.execute(
        "INSERT OR REPLACE INTO threads (thread_id, name) VALUES (?, ?)",
        (thread_id, name)
    )
    conn.commit()

conn.execute("""
    CREATE TABLE IF NOT EXISTS threads (
        thread_id TEXT PRIMARY KEY,
        name TEXT DEFAULT 'New Chat'
    )
    """)
conn.commit()

def retrieve_all_threads():
    cursor = conn.execute("SELECT thread_id, name FROM threads")
    rows = cursor.fetchall()
    return {row[0]: row[1] for row in rows}

def delete_thread(thread_id: str):
    conn.execute("DELETE FROM threads WHERE thread_id = ?", (thread_id,))
    conn.commit()

    # delete from langgraph checkpoints
    conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
    conn.commit()


def clear_all_threads_and_checkpoints():
    try:
        with conn:  # ensures atomic transaction
            # Clear your custom threads table
            conn.execute("DELETE FROM threads")
            
            # Clear LangGraph checkpoint tables
            conn.execute("DELETE FROM checkpoints")
        
        print("✅ All threads and checkpoints cleared.")
    except Exception as e:
        print(f"⚠️ Error while clearing: {e}")
