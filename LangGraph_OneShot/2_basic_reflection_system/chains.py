from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

generation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system", "You are a twitter techie influencer assistant tasked with writing excellent twitter posts."
            "Generate the best twitter post possible for the user's request"
            "if the user provide critique, response with a revised version of your previous attempts"
            ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

reflection_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system", "You are a viral twitter influencer grading a tweet, Generate critique and recommandations for user's tweet."
            "Always provide detailed recommandations, including requests for length, virality, style, etc"
            ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

generation_chain = generation_prompt | llm
reflection_chain = reflection_prompt | llm
