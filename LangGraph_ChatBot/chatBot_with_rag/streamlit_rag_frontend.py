import uuid
import asyncio
import streamlit as st
import langgraph_rag_backend
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage

FIRST_MESSAGE={"role": "system", "content": "Let's start chatting! 👇"}
def generate_thread_id():
    return str(uuid.uuid4())

if "db_initialized" not in st.session_state:
    asyncio.run(langgraph_rag_backend.init_db())
    st.session_state.db_initialized = True

def create_new_chat():
    new_id = generate_thread_id()
    asyncio.run(langgraph_rag_backend.save_thread_db(new_id, "New Chat"))
    st.session_state.threads[new_id] = "New Chat"
    st.session_state.active_thread = new_id
    st.session_state.messages = [FIRST_MESSAGE]
        

def load_chat_history(thread_id):
    """Fetches history from backend and formats for Streamlit."""
    messages = asyncio.run(langgraph_rag_backend.get_history(thread_id))
    formatted = [FIRST_MESSAGE]
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage) and msg.content:
            content = msg.content
            if isinstance(content, list):
                text_content = ""
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        text_content += part["text"]
                formatted.append({"role": "assistant", "content": text_content})
            else:
                formatted.append({"role": "assistant", "content": content})
    return formatted


st.title("Gyani-Baba Chatbot")

if "threads" not in st.session_state:
    all_threads = asyncio.run(langgraph_rag_backend.get_all_threads_db())
    if all_threads:
        st.session_state.threads = all_threads
        st.session_state.active_thread = list(all_threads.keys())[-1]
        st.session_state.messages = load_chat_history(st.session_state.active_thread)
    else:
        st.session_state.threads = {}
        create_new_chat()
    st.session_state.rename_mode = False 

# Ensure active thread exists in list (edge case handling)
if st.session_state.active_thread not in st.session_state.threads and st.session_state.threads:
    st.session_state.active_thread = list(st.session_state.threads.keys())[-1]

with st.sidebar:
    st.title("My Conversations")
    
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("➕ New Chat"):
            create_new_chat()
            st.rerun() 
    with col2:
        if st.button("🗑️ Delete Chat"):
            tid = st.session_state.active_thread
            asyncio.run(langgraph_rag_backend.delete_thread_db(tid))
            del st.session_state.threads[tid]
            
            if st.session_state.threads:
                st.session_state.active_thread = list(st.session_state.threads.keys())[-1]
                st.session_state.messages = load_chat_history(st.session_state.active_thread)
            else:
                create_new_chat()
            st.rerun()
    
    if st.button("🧹 Clear All Chats"):
        asyncio.run(langgraph_rag_backend.clear_db())
        st.session_state.threads = {}
        create_new_chat()
        st.rerun()
    
    if st.button("✏️ Rename Chat"):
        st.session_state.rename_mode = True
        st.rerun()

    st.header("📄 Upload Document")
    uploaded_file = st.file_uploader("Add PDF to this chat", type=["pdf"], key="pdf_uploader")
    if uploaded_file:
        if st.button("Process PDF"):
            with st.spinner("Uploading and Analyzing..."):
                file_bytes = uploaded_file.read()
                msg = langgraph_rag_backend.process_pdf(st.session_state.active_thread, file_bytes)
                if "Error" in msg:
                    st.error(msg)
                else:
                    st.success(msg)
    st.divider()

    if st.session_state.rename_mode:
        current_name = st.session_state.threads.get(st.session_state.active_thread, "New Chat")
        new_name = st.text_input("Enter new name:", value=current_name)

        c3, c4 = st.columns([1,1])
        if c3.button("✅ Save"):
            asyncio.run(langgraph_rag_backend.save_thread_db(st.session_state.active_thread, new_name))
            st.session_state.threads[st.session_state.active_thread] = new_name
            st.session_state.rename_mode = False
            st.rerun()
        if c4.button("❌ Cancel"):
            st.session_state.rename_mode = False
            st.rerun()
    
    thread_ids = list(st.session_state.threads.keys())[::-1] 
    if st.session_state.active_thread in thread_ids:
        idx = thread_ids.index(st.session_state.active_thread)
    else:
        idx = 0
    selected_id = st.radio(
        "Select a chat:",
        thread_ids,
        index=idx,
        format_func=lambda x: st.session_state.threads[x]
    )
    if selected_id != st.session_state.active_thread:
        st.session_state.active_thread = selected_id
        st.session_state.messages = load_chat_history(selected_id)
        st.rerun()
        
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

# Accept user input
if user_input := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("user"):
        st.markdown(user_input)


    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        async def run_chat():
            local_response = ""
            local_tool_status = None 
            if st.session_state.threads[st.session_state.active_thread] == "New Chat":
                 # Optional: Auto-rename logic could go here
                await langgraph_rag_backend.save_thread_db(st.session_state.active_thread, "New Chat")
            
            async for chunk, _ in langgraph_rag_backend.stream_chat(st.session_state.active_thread, user_input):
                if isinstance(chunk, ToolMessage):
                    tool_name = getattr(chunk, "name", "Tool")
                    if local_tool_status is None:
                        local_tool_status  = st.status(f"🔧 Using {tool_name}...", expanded=True)
                    else:
                        local_tool_status.update(label=f"🔧 Using {tool_name}...", state="running")
                
                if isinstance(chunk, AIMessage) and chunk.content:
                    content = chunk.content
                    
                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and "text" in part:
                                local_response += part["text"]
                    else:
                        local_response += content
                        
                    message_placeholder.markdown(local_response + "▌")

            message_placeholder.markdown(local_response)
            if local_tool_status:
                local_tool_status.update(label="✅ Tools Finished", state="complete", expanded=False)
            
            return local_response
        
        final_response = asyncio.run(run_chat())
        st.session_state.messages.append({"role": "assistant", "content": final_response})