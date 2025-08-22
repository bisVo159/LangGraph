from typing import List,Sequence
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage,BaseMessage,AIMessage
from langgraph.graph import END,MessageGraph
from chains import generation_chain,reflection_chain

load_dotenv()

graph=MessageGraph()

REFLECT="reflect"
GENERATE="generate"

def generate_node(state):
    """
    Generate a tweet based on the user's input.
    """
    response= generation_chain.invoke({
        "messages": state
    })
    return [AIMessage(content=response.content)]

def reflect_node(state):
    """
    Reflect on the generated tweet and provide critique.
    """
    # print(state)
    response= reflection_chain.invoke({
        "messages": state
    })
    return [HumanMessage(content=response.content)]

graph.add_node(GENERATE, generate_node)
graph.add_node(REFLECT, reflect_node)

graph.set_entry_point(GENERATE)

def should_continue(state: Sequence[BaseMessage]) -> str:
    return END if len(state) > 2 else REFLECT


graph.add_conditional_edges(GENERATE,should_continue,{END: END, REFLECT: REFLECT})
graph.add_edge(REFLECT, GENERATE)

app=graph.compile()

print(app.get_graph().draw_mermaid())
print(app.get_graph().draw_ascii())


response = app.invoke(HumanMessage(content="AI Agents taking over content creation"))

print(response)