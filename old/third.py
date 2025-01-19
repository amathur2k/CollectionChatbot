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
        new_messages = state["messages"] + [("assistant", response)]
        
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
        classification = classify_response(messages)
        
        print(f"Current step: {current_step}")
        print(f"Classification: {classification}")
        
        # Transition map based on current step
        transitions = {
            "greeting": {
                "yes speaking": "verification",
                "wrong number": "script_1",
                "call back": "script_3",
                "unknown": "greeting"  # Stay in greeting for unknown
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
                "unknown": "verification"
            },
            "discussion": {
                "discuss further": "transfer",
                "callback": "callback",
                "unknown": "discussion"
            }
        }
        
        # Get transitions for current step
        step_transitions = transitions.get(current_step, {})
        next_node = step_transitions.get(classification)
        
        print(f"Next node: {next_node}")
        return next_node if next_node else current_step  # Stay in current step if no valid transition
    
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
        return "unknown"
    
    try:
        # Get last user message
        for msg in reversed(messages):
            if isinstance(msg, tuple) and msg[0] == "user":
                content = msg[1]
                print(f"Found user message (tuple): {content}")  # Debug print
                break
            elif isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                print(f"Found user message (dict): {content}")  # Debug print
                break
            elif hasattr(msg, 'content'):  # For AIMessage/HumanMessage
                content = msg.content
                print(f"Found user message (Message): {content}")  # Debug print
                break
        else:
            print("No user message found")  # Debug print
            return "unknown"
            
        # Handle simple responses directly
        content_lower = content.lower().strip()
        print(f"Processing message: '{content_lower}'")  # Debug print
        
        # Simple responses that mean "yes speaking"
        simple_yes_responses = ["yes", "yeah", "yep", "correct", "speaking", "hi", "hello", "hey"]
        if any(content_lower == resp for resp in simple_yes_responses):
            print("Simple yes response detected")
            return "yes speaking"
            
        # Compound responses that mean "yes speaking"
        compound_yes_phrases = ["yes speaking", "yes this is", "that's me", "this is me"]
        if any(phrase in content_lower for phrase in compound_yes_phrases):
            print("Compound yes response detected")
            return "yes speaking"
            
        # Use LLM for more complex responses
        print("Using LLM for classification")  # Debug print
        result = classifier_chain.invoke({"response": content})
        classification = result.content.strip().lower()
        
        print(f"LLM classification: '{classification}'")
        return classification
        
    except Exception as e:
        print(f"Classification error: {str(e)}")
        return "unknown"

# Modified example usage
if __name__ == "__main__":
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
            chat_history.append(("user", user_input))  # Changed from dict to tuple
            
            # Create new conversation state
            state = {
                "messages": chat_history,
                "script": script_state
            }
            
            # Invoke graph with current state
            result = graph.invoke(state)
            
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
            
            # Check if we've reached an end state
            if result.get("end", False):
                print("\nConversation ended.")
                break
                
        except Exception as e:
            print(f"\nError: {str(e)}")
            print("Resetting conversation...")
            chat_history = []
            script_state = {
                "step": "greeting",
                "verified": False,
                "user_id": None
            }
