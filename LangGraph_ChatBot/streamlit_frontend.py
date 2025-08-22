import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage
import time

CONFIG = {'configurable': {'thread_id': 'thread-1'}}

st.title("Gyani-Baba Chatbot")


# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Let's start chatting! 👇"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if user_input := st.chat_input("What is up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(user_input)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        response = chatbot.invoke({"messages": [HumanMessage(content=user_input)]},config=CONFIG)
        ai_respose=response['messages'][-1].content
        # Simulate stream of response with milliseconds delay
        for chunk in ai_respose.split():
            full_response += chunk + " "
            time.sleep(0.05)
            # Add a blinking cursor to simulate typing
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
