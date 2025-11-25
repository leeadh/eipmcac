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
@st.cache_resource
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
                    
                    # Extract text content
                    response_text = ""
                    for content_block in latest_message.content:
                        if hasattr(content_block, 'text'):
                            response_text += content_block.text.value
                    
                    # Display the response
                    message_placeholder.markdown(response_text)
                    
                    # Add to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text
                    })
                else:
                    message_placeholder.markdown("❌ No response received.")
            
            elif run.status == 'requires_action':
                message_placeholder.markdown("⚠️ This request requires additional actions that are not yet supported.")
            
            else:
                message_placeholder.markdown(f"❌ Error: Run status is {run.status}")
        
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

