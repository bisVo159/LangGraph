from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import tool, create_react_agent
import datetime
from langchain_tavily import TavilySearch
from langchain import hub

llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash")

@tool
def get_system_time(format: str = "%Y-%m-%d %H:%M:%S"):
    """ Returns the current date and time in the specified format """

    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime(format)
    return formatted_time

search_tool = TavilySearch(search_depth="basic")
react_prompt = hub.pull("hwchase17/react")

tools = [get_system_time, search_tool]

react_agent_runnable = create_react_agent(tools=tools, llm=llm, prompt=react_prompt)