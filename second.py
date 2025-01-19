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

# Create the graph
def create_graph():
    # Initialize graph
    builder = StateGraph(State)
    
    # Add nodes
    builder.add_node("assistant", Assistant(assistant_runnable))
    builder.add_node("tools", ToolNode(tools))
    
    # Add edges
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        lambda x: "tools" if x.get("messages")[-1].tool_calls else END
    )
    builder.add_edge("tools", "assistant")
    
    # Compile graph
    return builder.compile()

# Create the graph instance
graph = create_graph()

# Modified example usage
if __name__ == "__main__":
    # Initialize chat history
    chat_history = []
    
    print("Chatbot initialized. Type 'quit' to exit.")
    while True:
        # Get user input
        user_input = input("\nYou: ").strip()
        
        # Check for quit command
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("\nGoodbye!")
            break
        
        # Add user message to history and invoke graph
        chat_history.append(("user", user_input))
        result = graph.invoke({"messages": chat_history})
        
        # Update chat history with the result
        chat_history = result["messages"]
        
        # Print assistant's response (last message)
        assistant_message = result["messages"][-1].content
        print("\nAssistant:", assistant_message)
