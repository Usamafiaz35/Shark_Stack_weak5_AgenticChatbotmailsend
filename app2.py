import asyncio
import streamlit as st
from dotenv import load_dotenv
from agents import Runner
from main import triage_agent
import os
import uuid
import time

# Load environment variables
load_dotenv()

# Generate session ID based on browser session
def get_session_id():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id

# Initialize conversation memory
def get_conversation_memory():
    if 'conversation_memory' not in st.session_state:
        st.session_state.conversation_memory = []
    return st.session_state.conversation_memory

# Build context from memory for agent
def build_conversation_context():
    memory = get_conversation_memory()
    if not memory:
        return ""
    
    # Build context string from recent messages
    context_lines = ["Previous conversation context:"]
    for msg in memory[-10:]:  # Last 10 messages only
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        context_lines.append(f"{role.title()}: {content}")
    
    context_lines.append("---")
    return "\n".join(context_lines)

# Streaming function for bot responses
def stream_text(text, placeholder):
    """Stream text character by character for better UX"""
    full_text = ""
    for char in text:
        full_text += char
        placeholder.markdown(f"""
        <div class="bot-message">
            <div class="bot-bubble">
                {full_text}<span style="animation: blink 1s infinite;">|</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(0.02)  # Adjust speed here
    
    # Final message without cursor
    placeholder.markdown(f"""
    <div class="bot-message">
        <div class="bot-bubble">
            {full_text}
            <div class="message-meta">Bot • just now</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Load environment variables
load_dotenv()

# Streamlit page config
st.set_page_config(
    page_title="Email Bot", 
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for WhatsApp-style chat
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        margin-bottom: 2rem;
    }
    
    /* Chat container */
    .chat-container {
        max-width: 100%;
        margin: 1rem 0;
    }
    
    /* User message (right side - WhatsApp style) */
    .user-message {
        display: flex;
        justify-content: flex-end;
        margin: 1rem 0;
    }
    
    .user-bubble {
        background: linear-gradient(135deg, #DCF8C6 0%, #C8E6C9 100%);
        color: #2E7D32;
        padding: 12px 16px;
        border-radius: 18px 18px 4px 18px;
        max-width: 75%;
        word-wrap: break-word;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        position: relative;
    }
    
    .user-bubble:after {
        content: '';
        position: absolute;
        bottom: 0;
        right: -8px;
        width: 0;
        height: 0;
        border: 8px solid transparent;
        border-top-color: #DCF8C6;
        border-bottom: 0;
        margin-left: -8px;
        margin-bottom: -8px;
    }
    
    /* Bot message (left side - WhatsApp style) */
    .bot-message {
        display: flex;
        justify-content: flex-start;
        margin: 1rem 0;
    }
    
    .bot-bubble {
        background: linear-gradient(135deg, #FFFFFF 0%, #F5F5F5 100%);
        color: #333333;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        max-width: 75%;
        word-wrap: break-word;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        position: relative;
        border: 1px solid #E0E0E0;
    }
    
    .bot-bubble:after {
        content: '';
        position: absolute;
        bottom: 0;
        left: -8px;
        width: 0;
        height: 0;
        border: 8px solid transparent;
        border-top-color: #FFFFFF;
        border-bottom: 0;
        margin-right: -8px;
        margin-bottom: -8px;
    }
    
    /* Message metadata */
    .message-meta {
        font-size: 0.7rem;
        color: #666;
        margin-top: 4px;
        text-align: right;
    }
    
    /* Bot typing indicator */
    .typing-indicator {
        display: flex;
        justify-content: flex-start;
        margin: 1rem 0;
    }
    
    .typing-bubble {
        background: #F5F5F5;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .typing-dots {
        display: inline-flex;
        align-items: center;
    }
    
    .typing-dots span {
        height: 8px;
        width: 8px;
        background: #999;
        border-radius: 50%;
        display: inline-block;
        margin: 0 2px;
        animation: typing 1.5s infinite ease-in-out;
    }
    
    .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
    .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
    
    @keyframes typing {
        0%, 60%, 100% { transform: translateY(0); }
        30% { transform: translateY(-10px); }
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0; }
    }
    
    /* Status boxes */
    .status-box {
        padding: 0.5rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-size: 0.85rem;
    }
    .status-success {
        background-color: #D4EDDA;
        border: 1px solid #C3E6CB;
        color: #155724;
    }
    .status-warning {
        background-color: #FFF3CD;
        border: 1px solid #FFEAA7;
        color: #856404;
    }
    .status-error {
        background-color: #F8D7DA;
        border: 1px solid #F5C6CB;
        color: #721C24;
    }
    
    /* Hide streamlit default elements */
    .stChatMessage { display: none !important; }
    
    /* Chat input styling */
    .stChatInput > div > div > div > div {
        border-radius: 25px !important;
        border: 2px solid #E0E0E0 !important;
    }
    
    /* Sidebar styling */
    .css-1d391kg { 
        background: linear-gradient(180deg, #F8F9FA 0%, #E9ECEF 100%);
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🤖 Email Bot")
    st.write("**Features:**")
    st.write("• General conversation")
    st.write("• Draft emails")
    st.write("• Send emails")
    
    # Environment status
    st.subheader("🔧 Configuration")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    email_address = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")
    
    if openai_key:
        st.markdown('<div class="status-box status-success">✅ OpenAI API Key: Connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-box status-error">❌ OpenAI API Key: Missing</div>', unsafe_allow_html=True)
    
    if email_address:
        st.markdown(f'<div class="status-box status-success">✅ Email: {email_address}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-box status-warning">⚠️ Email: Not configured</div>', unsafe_allow_html=True)
    
    if email_password:
        st.markdown('<div class="status-box status-success">✅ Email Password: Set</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-box status-warning">⚠️ Email Password: Not set</div>', unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("💾 Memory Status")
    session_id = get_session_id()
    memory = get_conversation_memory()
    st.write(f"**Session ID:** `{session_id[:8]}...`")
    st.write(f"**Messages in memory:** {len(memory)}")
    st.markdown('<div class="status-box status-success">✅ In-Memory conversation: Active</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # Instructions
    st.subheader("💡 How to use:")
    st.write("**For general chat:**")
    st.write("Just ask any question!")
    
    st.write("**To draft an email:**")
    st.write('Say: "Write an email" or "Draft an email"')
    
    st.write("**To send an email:**")
    st.write('Say: "Send an email" or "Send email to..."')
    
    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["conversation_memory"] = []  # Clear memory
        # Clear session ID to start fresh conversation
        if 'session_id' in st.session_state:
            del st.session_state['session_id']
        st.rerun()

# Main content
st.markdown('<h1 class="main-header">📧 Email Bot Assistant</h1>', unsafe_allow_html=True)

# Check API key
if not openai_key:
    st.error("🚨 OpenAI API Key is missing! Please add OPENAI_API_KEY to your .env file.")
    st.stop()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = []
    # Add welcome message
    welcome_msg = """👋 Hi! I'm your Email Bot assistant. I can help you with:

• **General questions** - Ask me anything!
• **Draft emails** - Say "write an email" and I'll help you compose it
• **Send emails** - Say "send an email" and I'll help you send it (if configured)

What would you like to do today?"""
    st.session_state["messages"].append(("assistant", welcome_msg))

# Display chat history with WhatsApp-style layout
for role, message in st.session_state["messages"]:
    if role == "user":
        st.markdown(f"""
        <div class="user-message">
            <div class="user-bubble">
                {message}
                <div class="message-meta">You • just now</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="bot-message">
            <div class="bot-bubble">
                {message}
                <div class="message-meta">Bot • just now</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Type your message here...")

if user_input:
    # Get conversation memory
    memory = get_conversation_memory()
    
    # Add user message to memory
    memory.append({"role": "user", "content": user_input})
    
    # Add user message to display history
    st.session_state["messages"].append(("user", user_input))
    
    # Display user message immediately with WhatsApp style
    st.markdown(f"""
    <div class="user-message">
        <div class="user-bubble">
            {user_input}
            <div class="message-meta">You • just now</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Show typing indicator
    typing_placeholder = st.empty()
    typing_placeholder.markdown("""
    <div class="typing-indicator">
        <div class="typing-bubble">
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <span style="margin-left: 10px; color: #666; font-size: 0.8rem;">Bot is typing...</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # Build context from conversation history
        context = build_conversation_context()
        
        # Create input with context if memory exists
        if len(memory) > 1:  # More than just current message
            contextual_input = f"{context}\n\nCurrent message: {user_input}"
        else:
            contextual_input = user_input
        
        # Run the agent with contextual input
        result = asyncio.run(Runner.run(triage_agent, contextual_input))
        bot_reply = result.final_output
        
        # Clear typing indicator
        typing_placeholder.empty()
        
        # Add bot response to memory
        memory.append({"role": "assistant", "content": bot_reply})
        
        # Add bot response to display history
        st.session_state["messages"].append(("assistant", bot_reply))
        
        # Stream bot response with WhatsApp style
        response_placeholder = st.empty()
        stream_text(bot_reply, response_placeholder)
        
        # Small delay then rerun to show complete conversation
        time.sleep(0.5)
        st.rerun()
        
    except Exception as e:
        typing_placeholder.empty()
        error_message = f"❌ Sorry, I encountered an error: {str(e)}"
        
        st.markdown(f"""
        <div class="bot-message">
            <div class="bot-bubble" style="background: #FFEBEE; border-color: #FFCDD2;">
                {error_message}
                <div class="message-meta">Bot • just now</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.session_state["messages"].append(("assistant", error_message))
        memory.append({"role": "assistant", "content": error_message})
        time.sleep(1)
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    '''
    <div style="text-align: center; color: #666; font-size: 0.8rem; padding: 20px;">
        Made with ❤️ using Streamlit & OpenAI Agents<br>
        <span style="font-size: 0.7rem;">💬 WhatsApp-style chat • 🚀 Streaming responses • 🧠 Memory enabled</span>
    </div>
    ''',
    unsafe_allow_html=True
)