import uuid
import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage

FIRST_MESSAGE={"role": "system", "content": "Let's start chatting! 👇"}
def generate_thread_id():
    return str(uuid.uuid4())

def add_thread(thread_id,title="New Chat"):
    if thread_id not in st.session_state.threads:
        st.session_state.threads[thread_id] = title

def load_conversation(thread_id):
    try:
        backend_messages = chatbot.get_state(
            config={'configurable': {'thread_id': thread_id}}
        ).values.get('messages',[])

        temp_messages = [FIRST_MESSAGE]
        for msg in backend_messages:
            if isinstance(msg, HumanMessage):
                temp_messages.append({"role": "user", "content": msg.content})
            else :  
                temp_messages.append({"role": "assistant", "content": msg.content})

        st.session_state.messages = temp_messages

    except Exception as e:
        st.session_state.messages= [{"role": "assistant", "content": f"⚠️ Error loading conversation: {e}"}]


def reset_chat():
    new_uuid = generate_thread_id()
    add_thread(new_uuid)
    st.session_state.active_thread = new_uuid
    st.session_state['messages']=[FIRST_MESSAGE]

st.title("Gyani-Baba Chatbot")

if "threads" not in st.session_state:
    first_uuid = generate_thread_id()
    st.session_state.threads = {first_uuid: "New Chat"}
    st.session_state.messages = [FIRST_MESSAGE]
    st.session_state.active_thread = first_uuid
    st.session_state.rename_mode = False

with st.sidebar:
    st.title("My Conversations")
    if st.button("➕ New Chat"):
        reset_chat()
    
    if st.button("✏️ Rename Chat"):
        st.session_state.rename_mode= True
        st.rerun()

    if st.session_state.rename_mode:
        new_name = st.text_input(
            "Enter new name:",
            value=st.session_state.threads[st.session_state.active_thread],
            key="rename_input"
        )

        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("✅ Save", key="rename_save"):
                st.session_state.threads[st.session_state.active_thread] = new_name
                st.session_state.rename_mode = False
                st.rerun()

        with col2:
            if st.button("❌ Cancel", key="rename_cancel"):
                st.session_state.rename_mode = False
                st.rerun()

    thread_keys = list(st.session_state.threads.keys())[::-1]
    selected_thread =st.radio(
        "Select a chat:",
        thread_keys,
        index=thread_keys.index(st.session_state.active_thread),
        format_func=lambda tid: st.session_state.threads[tid]
    )
    if selected_thread != st.session_state.active_thread:
        st.session_state.active_thread=selected_thread
        load_conversation(selected_thread) 
        st.rerun()

active_thread = st.session_state.active_thread
CONFIG = {'configurable': {'thread_id': active_thread}}

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"],unsafe_allow_html=True)

# Accept user input
if user_input := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input,unsafe_allow_html=True)

    with st.chat_message("assistant"):
        ai_response=st.write_stream(
            message_chunk.content for message_chunk,metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages"
            )
        )
        
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
