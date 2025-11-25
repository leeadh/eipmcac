import os
import time
import streamlit as st
from openai import AzureOpenAI

# Page configuration
st.set_page_config(
    page_title="MindChamps Allied Care Assistant",
    page_icon="🧠",
    layout="wide"
)

# Initialize Azure OpenAI client
def get_client(api_key, endpoint):
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-05-01-preview"
    )

# Custom CSS for better styling
st.markdown("""
    <style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .main {
        background-color: #f5f7fa;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("🧠 MindChamps Allied Care Assistant")
st.markdown("Ask me anything about MindChamps Allied Care services, therapists, programs, and more!")

# API Configuration Section
st.markdown("### 🔑 Configuration")

col1, col2 = st.columns(2)

with col1:
    azure_endpoint = st.text_input(
        "Azure OpenAI Endpoint",
        value="https://adrianleeopenai.openai.azure.com/",
        help="Enter your Azure OpenAI endpoint URL",
        type="default"
    )

with col2:
    azure_api_key = st.text_input(
        "Azure OpenAI API Key",
        type="password",
        help="Enter your Azure OpenAI API key"
    )

assistant_id = st.text_input(
    "Assistant ID",
    value="asst_Bts3TWKJpul7D9mc0fAfEd25",
    help="Enter your Azure OpenAI Assistant ID"
)

# Check if credentials are provided
if not azure_api_key:
    st.info("👆 Please add your Azure OpenAI API key to continue.", icon="🗝️")
    st.stop()

if not azure_endpoint:
    st.warning("Please enter your Azure OpenAI endpoint.", icon="⚠️")
    st.stop()

if not assistant_id:
    st.warning("Please enter your Assistant ID.", icon="⚠️")
    st.stop()

# Initialize client with provided credentials
try:
    client = get_client(azure_api_key, azure_endpoint)
    
    # Verify assistant exists and get its configuration
    try:
        assistant = client.beta.assistants.retrieve(assistant_id)
        st.success(f"✅ Connected to assistant: **{assistant.name or assistant_id}**", icon="✅")
        
        # Show if file_search is enabled
        if assistant.tools:
            tools_list = [tool.type for tool in assistant.tools]
            if 'file_search' in tools_list:
                st.info("🔍 File search is enabled - the assistant can search through uploaded documents.", icon="ℹ️")
    except Exception as e:
        st.warning(f"⚠️ Could not verify assistant: {str(e)}")
        
except Exception as e:
    st.error(f"Error initializing client: {str(e)}")
    st.stop()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    # Create a new thread for this session
    try:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        st.info(f"📝 New conversation started (Thread ID: {thread.id[:20]}...)", icon="ℹ️")
    except Exception as e:
        st.error(f"Error creating thread: {str(e)}")
        st.stop()

st.divider()

# Sidebar with info
with st.sidebar:
    st.header("About")
    st.markdown("""
    This assistant can help you with:
    - **Early Intervention (EIP)**
    - **Speech Therapy (ST)**
    - **Occupational Therapy (OT)**
    - **Child Psychology**
    - **Developmental Screening**
    - **Admin / Fees / Enrolment**
    
    ---
    
    📍 **Locations:**
    - Tampines
    - Toa Payoh
    
    🌐 [Visit Website](https://www.mindchamps-alliedcare.com/)
    """)
    
    if st.button("🔄 New Conversation"):
        st.session_state.messages = []
        try:
            thread = client.beta.threads.create()
            st.session_state.thread_id = thread.id
            st.rerun()
        except Exception as e:
            st.error(f"Error creating new thread: {str(e)}")
    
    st.divider()
    
    # Debug information
    with st.expander("🔧 Debug Info"):
        st.text(f"Thread ID: {st.session_state.get('thread_id', 'N/A')}")
        st.text(f"Assistant ID: {assistant_id}")
        st.text(f"Messages in history: {len(st.session_state.messages)}")
        
        if st.button("🔍 Check Assistant Config"):
            try:
                asst = client.beta.assistants.retrieve(assistant_id)
                st.json({
                    "name": asst.name,
                    "model": asst.model,
                    "instructions": asst.instructions[:200] + "..." if asst.instructions else None,
                    "tools": [tool.type for tool in asst.tools] if asst.tools else [],
                    "has_vector_store": bool(asst.tool_resources and 
                                           asst.tool_resources.file_search and 
                                           asst.tool_resources.file_search.vector_store_ids)
                })
            except Exception as e:
                st.error(f"Error: {e}")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response with spinner
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🔍 Searching through files...")
        
        try:
            # Add message to thread
            client.beta.threads.messages.create(
                thread_id=st.session_state.thread_id,
                role="user",
                content=prompt
            )
            
            # Run the assistant
            run = client.beta.threads.runs.create(
                thread_id=st.session_state.thread_id,
                assistant_id=assistant_id
            )
            
            # Poll for completion
            while run.status in ['queued', 'in_progress', 'cancelling']:
                time.sleep(0.5)
                run = client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id
                )
            
            if run.status == 'completed':
                # Get messages
                messages = client.beta.threads.messages.list(
                    thread_id=st.session_state.thread_id
                )
                
                # Get the latest assistant message
                assistant_messages = [
                    msg for msg in messages.data 
                    if msg.role == 'assistant' and msg.run_id == run.id
                ]
                
                if assistant_messages:
                    # Get the last assistant message
                    latest_message = assistant_messages[0]
                    
                    # Extract text content and citations
                    response_text = ""
                    citations = []
                    
                    for content_block in latest_message.content:
                        if hasattr(content_block, 'text'):
                            text_obj = content_block.text
                            response_text += text_obj.value
                            
                            # Extract file citations
                            if hasattr(text_obj, 'annotations') and text_obj.annotations:
                                for annotation in text_obj.annotations:
                                    if hasattr(annotation, 'file_citation'):
                                        citations.append(annotation.file_citation.file_id)
                    
                    # Display the response
                    message_placeholder.markdown(response_text)
                    
                    # Show citations if available
                    if citations:
                        with st.expander("📚 Sources", expanded=False):
                            st.write(f"Response generated from {len(citations)} file citation(s)")
                            for idx, file_id in enumerate(set(citations), 1):
                                st.text(f"{idx}. File ID: {file_id}")
                    
                    # Add to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text
                    })
                else:
                    message_placeholder.markdown("❌ No response received from assistant.")
                    st.error(f"Debug: Found {len(messages.data)} total messages, but none from this run.")
            
            elif run.status == 'requires_action':
                message_placeholder.markdown("⚠️ This request requires additional actions that are not yet supported.")
                st.error(f"Debug: Run requires action - {run.required_action}")
            
            elif run.status == 'failed':
                message_placeholder.markdown(f"❌ Assistant run failed.")
                if hasattr(run, 'last_error') and run.last_error:
                    st.error(f"Error details: {run.last_error.message}")
            
            else:
                message_placeholder.markdown(f"❌ Error: Run status is {run.status}")
                st.error(f"Debug info: {run}")
        
        except Exception as e:
            message_placeholder.markdown(f"❌ Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "Powered by Azure OpenAI | MindChamps Allied Care"
    "</div>",
    unsafe_allow_html=True
)

