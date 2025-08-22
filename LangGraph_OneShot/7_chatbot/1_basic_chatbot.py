from typing import TypedDict, Annotated
from langgraph.graph import add_messages, StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

llm=ChatGroq(model='llama-3.3-70b-versatile')

class BasicChatState(TypedDict):
    messages: Annotated[list, add_messages]

def chatbot(state: BasicChatState):
    return {
        "messages": AIMessage(llm.invoke(state["messages"]).content)
    }

graph = StateGraph(BasicChatState)

graph.add_node("chatbot", chatbot)
graph.set_entry_point("chatbot")
graph.add_edge("chatbot", END)

app = graph.compile()

while True: 
    user_input = input("User: ")
    if(user_input in ["exit", "end"]):
        break
    else: 
        result = app.invoke({
            "messages": [HumanMessage(content=user_input)]
        })

        print(result)