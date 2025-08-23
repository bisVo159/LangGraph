from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import  BaseMessage,HumanMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv
import sqlite3

load_dotenv()
llm=ChatGoogleGenerativeAI(model="gemini-2.5-flash")
conn=sqlite3.connect(database='ChatBot.db',check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)
    
    return {"messages":[response]}

graph=StateGraph(ChatState)
graph.add_node("chat_node",chat_node)

graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot=graph.compile(checkpointer=checkpointer)

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


# def clear_all_threads_and_checkpoints(conn: sqlite3.Connection):
#     try:
#         with conn:  # ensures atomic transaction
#             # Clear your custom threads table
#             conn.execute("DELETE FROM threads")
            
#             # Clear LangGraph checkpoint tables
#             conn.execute("DELETE FROM checkpoints")
#             # conn.execute("DELETE FROM checkpoint_blobs")
#             # conn.execute("DELETE FROM checkpoint_writes")
        
#         print("✅ All threads and checkpoints cleared.")
#     except Exception as e:
#         print(f"⚠️ Error while clearing: {e}")

# clear_all_threads_and_checkpoints(conn)