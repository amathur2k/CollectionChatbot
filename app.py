import streamlit as st
from horse import MultiAgentDebtCollectionBot

# Page config
st.set_page_config(
    page_title="Debt Collection Bot",
    page_icon="💬",
    layout="centered"
)

# Initialize session state
if 'bot' not in st.session_state:
    st.session_state.bot = MultiAgentDebtCollectionBot()
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Title
st.title("💬 Debt Collection Assistant")

# Clear chat button
if st.sidebar.button("Clear Conversation", type="primary"):
    st.session_state.messages = []
    st.session_state.bot.clear_history()
    st.rerun()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Get and display bot response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = st.session_state.bot.get_response(prompt)
            st.write(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

# Sidebar info
with st.sidebar:
    st.markdown("""
    ### About
    This is a multi-agent debt collection chatbot that can:
    - Verify identity
    - Discuss payment plans
    - Schedule callbacks
    - Process payments
    
    ### Instructions
    1. Start by saying hello
    2. Follow the bot's instructions
    3. Use 'Clear Conversation' to start over
    """) 