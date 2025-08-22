from langchain.agents import initialize_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import TavilySearchResults
from langchain_core.tools import tool
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

search_tool = TavilySearchResults()

@tool
def get_current_datetime()-> str:
    """
    Returns the current date and time in ISO format: YYYY-MM-DD HH:MM:SS
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

tools = [search_tool,get_current_datetime]

agent=initialize_agent(
    tools=tools,
    llm=llm,
    agent="conversational-react-description",
    verbose=True
)

def run_agent(query):
    response = agent.invoke(query)
    return response

if __name__ == "__main__":
    query = "when was spacex last launch and how many days ago from this instant"
    response = run_agent(query)
    print(response)