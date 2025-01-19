from typing import Annotated, TypedDict
from typing_extensions import TypedDict
from datetime import datetime

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AnyMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from graphviz import Digraph
import tempfile
import webbrowser
import os

# Define the state
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

# Mock database of debts
DEBT_DATABASE = {
    "USER123": {
        "name": "John Doe",
        "amount": 5000,
        "due_date": "2024-03-01",
        "minimum_payment": 500,
        "status": "overdue"
    },
    "USER456": {
        "name": "Jane Smith",
        "amount": 2500,
        "due_date": "2024-04-15",
        "minimum_payment": 250,
        "status": "current"
    }
}

# Define debt-related tools
@tool
def get_debt_info(user_id: str) -> str:
    """Get debt information for a specific user."""
    if user_id in DEBT_DATABASE:
        debt = DEBT_DATABASE[user_id]
        return f"Name: {debt['name']}\nAmount: ${debt['amount']}\nDue Date: {debt['due_date']}\nMinimum Payment: ${debt['minimum_payment']}\nStatus: {debt['status']}"
    return "User not found in database."

@tool
def calculate_payment_plan(user_id: str, months: int) -> str:
    """Calculate monthly payment plan for a user's debt."""
    if user_id in DEBT_DATABASE:
        debt = DEBT_DATABASE[user_id]
        monthly_payment = debt['amount'] / months
        return f"For a {months}-month payment plan:\nMonthly payment would be: ${monthly_payment:.2f}"
    return "User not found in database."

@tool
def get_minimum_payment(user_id: str) -> str:
    """Get the minimum payment amount for a user."""
    if user_id in DEBT_DATABASE:
        return f"Minimum payment required: ${DEBT_DATABASE[user_id]['minimum_payment']}"
    return "User not found in database."

# Create the assistant
class Assistant:
    def __init__(self, runnable):
        self.runnable = runnable

    def __call__(self, state: State):
        result = self.runnable.invoke(state)
        return {"messages": result}

# Set up the LLM and prompt
llm = ChatAnthropic(model="claude-3-sonnet-20240229")

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a professional and empathetic debt recovery agent. Your role is to:
    1. Help users understand their debt situation
    2. Provide payment plan options
    3. Explain minimum payment requirements
    4. Be firm but understanding about payment obligations
    5. Always maintain a professional and respectful tone
    
    When users provide their ID, use the tools to look up their information.
    Common IDs in the system are: USER123 and USER456.
    
    Use the provided tools to assist users with their debt-related queries."""),
    ("placeholder", "{messages}")
])

# Create tools list and assistant runnable
tools = [get_debt_info, calculate_payment_plan, get_minimum_payment]
assistant_runnable = prompt | llm.bind_tools(tools)

# Define script states as nodes
class ScriptState(TypedDict):
    step: str
    verified: bool
    user_id: str | None
    callback_time: str | None

class ScriptNode:
    def __init__(self, script_id: str, response_template: str):
        self.script_id = script_id
        self.response_template = response_template
    
    def __call__(self, state: State):
        customer_info = {
            "debtor_name": "John Doe",
            "amount": "5,000",
            "product": "Credit Card",
            "bank_name": "DBank"
        }
        
        response = self.response_template.format(**customer_info)
        
        # Convert all messages to tuples for consistency
        current_messages = []
        for msg in state["messages"]:
            if isinstance(msg, tuple):
                current_messages.append(msg)
            elif hasattr(msg, 'type'):
                role = "user" if msg.type == "human" else "assistant"
                current_messages.append((role, msg.content))
            elif isinstance(msg, dict):
                current_messages.append((msg.get("role", "unknown"), msg.get("content", "")))
        
        new_messages = current_messages + [("assistant", response)]
        
        return {
            "messages": new_messages,
            "script": {
                "step": self.script_id,
                "verified": state.get("script", {}).get("verified", False),
                "user_id": state.get("script", {}).get("user_id", None)
            }
        }

def create_graph():
    builder = StateGraph(State)
    
    # Define script responses based on the actual script
    builder.add_node("greeting", ScriptNode(
        "greeting",
        "Good morning/afternoon/evening. My name is AI Agent calling from {bank_name}. "
        "May I speak with {debtor_name}?"
    ))
    
    builder.add_node("verification", ScriptNode(
        "verification",
        "To ensure I am speaking with the correct person, may I confirm your last 4 digits "
        "of your IC number or Date of Birth please?"
    ))
    
    builder.add_node("discussion", ScriptNode(
        "discussion",
        "The reason for this call is to inform you that your {product} account formerly from "
        "{bank_name} is still outstanding for RM{amount} and we would like to assist you in "
        "working out payment plan options that might work for you. Would you be open to "
        "discussing a plan that fits you?"
    ))
    
    # Add transfer and callback nodes
    builder.add_node("transfer", ScriptNode(
        "transfer",
        "Thank you for your cooperation. I will be connecting this call to the Credit Management "
        "officer in charge of your account for further discussion. Please hold the line."
    ))
    
    builder.add_node("callback", ScriptNode(
        "callback",
        "We have noted your request for a callback. Would you please confirm your preferred "
        "date and time for the discussion?"
    ))
    
    # Add all handling script nodes first
    script_responses = {
        "script_1": "I understand this is a wrong number. I apologize for the inconvenience. Have a good day.",
        "script_3": "I understand this isn't a good time. When would be a better time to call back?",
        "script_4": "I assure you this is a legitimate call from {bank_name}. You can verify this by...",
        "script_5": "Let me check our records regarding the settlement...",
        "script_6": "I'll verify the account details again...",
        "script_7": "I understand your concern about fraud. Let me provide our bank's verification details...",
        "script_8": "I understand your concern. Let me provide you with our bank's official contact information...",
        "script_9": "I understand you wish to report to the central bank. Let me provide our banking license details...",
        "script_10": "Let me check the account status regarding the time bar claim...",
        "script_11": "I understand your position. However, let's discuss why settling this would benefit you...",
        "script_13": "I understand your financial situation. Let's discuss flexible payment options...",
        "script_14": "I'm sorry to hear about your health. Let's discuss options that consider your situation..."
    }
    
    # Create all script nodes
    for script_id, response in script_responses.items():
        builder.add_node(script_id, ScriptNode(script_id, response))
    
    # Define edge conditions
    def get_next_node(state):
        messages = state["messages"]
        current_step = state.get("script", {}).get("step", "greeting")
        print(f"\nDEBUG: State before classification: {state}")
        classification = classify_response(messages)
        
        print(f"DEBUG: Current step: {current_step}")
        print(f"DEBUG: Classification result: {classification}")
        
        # Transition map based on current step
        transitions = {
            "greeting": {
                "yes speaking": "verification",
                "wrong number": "script_1",
                "call back": "script_3",
                "unknown": END,
                "end": END
            },
            "verification": {
                "verified": "discussion",
                "why verify": "script_3",
                "scammer": "script_4",
                "settled": "script_5",
                "no account": "script_6",
                "fraud": "script_7",
                "police": "script_8",
                "central bank": "script_9",
                "time barred": "script_10",
                "wont pay": "script_11",
                "cant afford": "script_13",
                "jobless": "script_13",
                "sick": "script_14",
                "unknown": END,
                "end": END
            },
            "discussion": {
                "discuss further": "transfer",
                "callback": "callback",
                "unknown": END,
                "end": END
            }
        }
        
        # Get transitions for current step
        step_transitions = transitions.get(current_step, {})
        print(f"DEBUG: Available transitions for {current_step}: {step_transitions}")
        next_node = step_transitions.get(classification)
        
        print(f"DEBUG: Selected next node: {next_node}")
        return next_node if next_node else END
    
    # Add edges with the new condition function
    builder.add_edge(START, "greeting")
    
    # Add conditional edges for each node
    for node in ["greeting", "verification", "discussion"] + list(script_responses.keys()):
        builder.add_conditional_edges(
            node,
            lambda x: get_next_node(x)
        )
    
    # Add termination paths
    builder.add_edge("transfer", END)
    builder.add_edge("callback", END)
    builder.add_edge("script_1", END)
    
    return builder.compile()

# Update the system prompt for state classification
state_classifier_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a debt collection call flow analyzer. Your job is to classify customer responses 
    according to the following script flow:

    GREETING RESPONSES:
    - "yes speaking" = Customer confirms identity
    - "wrong number" = Customer indicates wrong number
    - "call back" = Customer requests callback
    
    VERIFICATION RESPONSES:
    - "verified" = Customer provides IC/DOB
    - "why verify" = Customer questions verification
    - "scammer" = Customer suspects scam
    - "settled" = Claims already settled
    - "no account" = Claims no account
    - "fraud" = Claims fraud
    - "police" = Threatens police
    - "central bank" = Threatens central bank report
    - "time barred" = Claims time bar
    - "wont pay" = Refuses to pay
    - "cant afford" = Claims inability to pay
    - "jobless" = Claims unemployment
    - "sick" = Claims illness
    
    DISCUSSION RESPONSES:
    - "discuss further" = Willing to discuss payment
    - "callback" = Requests callback
    
    Analyze the customer's response and return ONLY ONE of the above classifications in lowercase, 
    or "unknown" if none match. Do not provide any explanation."""),
    ("human", "Customer response: {response}")
])

# Create classifier chain
classifier_chain = state_classifier_prompt | llm

def classify_response(messages: list) -> str:
    """Use LLM to classify the last user response."""
    if not messages:
        print("DEBUG: No messages found")
        return "unknown"
    
    try:
        # Get last user message
        print(f"DEBUG: Scanning messages: {messages}")
        content = None
        for msg in reversed(messages):
            # Handle both tuple and Message object formats
            if isinstance(msg, tuple) and msg[0] == "user":
                content = msg[1]
                print(f"DEBUG: Found user message (tuple): {content}")
                break
            elif hasattr(msg, 'type') and msg.type == 'human':
                content = msg.content
                print(f"DEBUG: Found user message (LangChain): {content}")
                break
            elif isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                print(f"DEBUG: Found user message (dict): {content}")
                break
        
        if content is None:
            print("DEBUG: No user message found in history")
            return "unknown"
            
        # Handle initial greetings immediately without LLM
        content_lower = content.lower().strip()
        print(f"DEBUG: Processing message: '{content_lower}'")
        
        # Expanded greeting detection
        if any(word in content_lower for word in ["hi", "hello", "hey", "yes", "speaking", "correct"]):
            print("DEBUG: Greeting/confirmation detected - classifying as 'yes speaking'")
            return "yes speaking"
            
        # Use LLM for classification
        print(f"DEBUG: Sending to LLM for classification: '{content}'")
        result = classifier_chain.invoke({"response": content})
        classification = result.content.strip().lower()
        
        print(f"DEBUG: LLM classification result: '{classification}'")
        return classification
        
    except Exception as e:
        print(f"DEBUG: Classification error: {str(e)}")
        return "end"

def visualize_graph():
    """Create and display a visualization of the debt collection call flow graph."""
    dot = Digraph(comment='Debt Collection Call Flow')
    dot.attr(rankdir='LR')  # Left to right layout
    
    # Add nodes
    dot.node('START', 'START', shape='circle')
    dot.node('END', 'END', shape='doublecircle')
    
    # Main flow nodes
    main_nodes = ['greeting', 'verification', 'discussion', 'transfer', 'callback']
    for node in main_nodes:
        dot.node(node, node.capitalize(), shape='box')
    
    # Script response nodes
    script_nodes = [
        'script_1', 'script_3', 'script_4', 'script_5', 'script_6', 
        'script_7', 'script_8', 'script_9', 'script_10', 'script_11',
        'script_13', 'script_14'
    ]
    for node in script_nodes:
        dot.node(node, node, shape='box', style='rounded')
    
    # Add edges
    dot.edge('START', 'greeting')
    
    # Greeting transitions
    dot.edge('greeting', 'verification', 'yes speaking')
    dot.edge('greeting', 'script_1', 'wrong number')
    dot.edge('greeting', 'script_3', 'call back')
    dot.edge('greeting', 'END', 'unknown/end')
    
    # Verification transitions
    dot.edge('verification', 'discussion', 'verified')
    dot.edge('verification', 'script_3', 'why verify')
    dot.edge('verification', 'script_4', 'scammer')
    dot.edge('verification', 'script_5', 'settled')
    dot.edge('verification', 'script_6', 'no account')
    dot.edge('verification', 'script_7', 'fraud')
    dot.edge('verification', 'script_8', 'police')
    dot.edge('verification', 'script_9', 'central bank')
    dot.edge('verification', 'script_10', 'time barred')
    dot.edge('verification', 'script_11', 'wont pay')
    dot.edge('verification', 'script_13', 'cant afford/jobless')
    dot.edge('verification', 'script_14', 'sick')
    dot.edge('verification', 'END', 'unknown/end')
    
    # Discussion transitions
    dot.edge('discussion', 'transfer', 'discuss further')
    dot.edge('discussion', 'callback', 'callback')
    dot.edge('discussion', 'END', 'unknown/end')
    
    # Terminal transitions
    dot.edge('transfer', 'END')
    dot.edge('callback', 'END')
    dot.edge('script_1', 'END')
    
    # Modified file handling
    try:
        # Use current directory instead of temp directory
        output_path = os.path.join(os.getcwd(), 'call_flow_graph')
        dot.render(output_path, format='svg', cleanup=True)
        webbrowser.open('file://' + output_path + '.svg')
    except Exception as e:
        print(f"Failed to create visualization: {str(e)}")
        print("You can still continue with the conversation.")

# Modified example usage
if __name__ == "__main__":
    # Add this line to visualize the graph before starting the conversation
    visualize_graph()
    
    # Initialize chat history and script state
    chat_history = []
    script_state = {
        "step": "greeting",
        "verified": False,
        "user_id": None
    }
    
    # Create graph
    graph = create_graph()
    
    print("Debt Collection Agent initialized. Type 'quit' to exit.")
    while True:
        try:
            # Get user input
            user_input = input("\nDebtor: ").strip()
            
            # Check for quit command
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\nCall ended.")
                break
            
            # Add user message to history
            print(f"\nDEBUG: Adding user input to history: {user_input}")
            chat_history.append(("user", user_input))
            print(f"DEBUG: Current chat history: {chat_history}")
            
            # Create new conversation state
            state = {
                "messages": chat_history,
                "script": script_state
            }
            
            # Invoke graph with current state
            print("\nDEBUG: Invoking graph with state:", state)
            result = graph.invoke(state)
            print(f"DEBUG: Graph result: {result}")
            
            # Update chat history and script state
            chat_history = result["messages"]
            script_state = result.get("script", script_state)
            
            # Print assistant's response
            try:
                last_message = result["messages"][-1]
                if isinstance(last_message, tuple):
                    print("\nAgent:", last_message[1])
                else:
                    print("\nAgent:", last_message.content)
            except (IndexError, AttributeError) as e:
                print("\nNo response generated")
                print(f"DEBUG: Error getting response: {str(e)}")
            
            # Check if we've reached an end state
            if result.get("end", False):
                print("\nConversation ended.")
                break
                
        except Exception as e:
            print(f"\nDEBUG: Main loop error: {str(e)}")
            print("Resetting conversation...")
            chat_history = []
            script_state = {
                "step": "greeting",
                "verified": False,
                "user_id": None
            }
