import getpass
import os
from datetime import datetime
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph.message import AnyMessage, add_messages

# Prompt for keys if not supplied
def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("ANTHROPIC_API_KEY")
_set_env("OPENAI_API_KEY")
# Normally TAVILY_API_KEY could be prompted, but the user said "no new tools",
# so we won't rely on Tavily for anything else here:
os.environ["TAVILY_API_KEY"] = ""

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        """Invoke the LLM once, greet the user, then return. 
           If the route_branch sends control back here later, 
           it will invoke the LLM again but only once per route."""
        
        # 1) Convert any LangChain messages to (role, text) tuples:
        updated_messages = []
        for msg in state["messages"]:
            if hasattr(msg, 'content'):  # It's a LangChain Message object
                role = msg.__class__.__name__.lower().replace('message', '')
                updated_messages.append((role, msg.content))
            else:
                updated_messages.append(msg)

        # 2) Include any config data
        configuration = config.get("configurable", {})
        passenger_id = configuration.get("passenger_id", None)
        # Repack the state for the LLM
        llm_input = {
            "messages": updated_messages,
            "user_info": passenger_id,
        }

        # 3) Call the LLM once
        print("\n[Assistant Debug] Invoking LLM with state:", llm_input)
        result = self.runnable.invoke(llm_input)
        print("[Assistant Debug] LLM result:", result)

        # 4) Convert result.content to a string and append as assistant message
        final_content = str(result.content) if result.content else ""
        updated_messages.append(("assistant", final_content))

        # 5) Return the new state with updated messages
        new_state = {"messages": updated_messages}
        print("[Assistant Debug] Returning state:", new_state)
        return new_state

# Use ChatAnthropic as before, no additional tools:
llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=1)

# Basic prompt that welcomes user and includes the current time
primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful polite debt recovery agent, greet the user with "
            "'Good morning/Afternoon/Evening Sir/Miss/Mdm. My name is <Name of the caller> "
            "calling from <bank name> and I would like to speak with <Debtor's Full Name>.' "
            "\nCurrent time: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now)

part_1_assistant_runnable = primary_assistant_prompt | llm

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START

builder = StateGraph(State)

# -----------------------------
# A simple Verification node
# -----------------------------
class Verification:
    def __call__(self, state: State, config: RunnableConfig):
        messages = state["messages"]
        # Demo for further verification steps:
        messages.append(
            (
                "assistant",
                "Thank you for confirming. Let's proceed with the verification process."
            )
        )
        return {"messages": messages}

# -----------------------------
# Condition: if user says "yes," "ok," etc., route to Verification
# else route back to Assistant
# -----------------------------
def user_agree_condition(state: State) -> bool:
    """Check if the last user message indicates agreement/confirmation."""
    if not state.get("messages"):
        return False

    last_message = state["messages"][-1]
    if isinstance(last_message, tuple):
        last_msg_text = last_message[1].lower()
    elif hasattr(last_message, "content"):
        last_msg_text = last_message.content.lower()
    else:
        return False

    accept_phrases = ["yes speaking", "yes i am speaking", "ok", "yes", "speaking"]
    return any(phrase in last_msg_text for phrase in accept_phrases)

# We define a single routing function that chooses either "verification" or "assistant"
def route_branch(state: State) -> str:
    """Route to either 'verification' or end the graph if user does not agree."""
    if user_agree_condition(state):
        return "verification"
    else:
        # Return "END" as a string. We'll map it to the actual END node below.
        return "END"

# -----------------------------
# Define the nodes
# -----------------------------
builder.add_node("assistant", Assistant(part_1_assistant_runnable))
builder.add_node("verification", Verification())

# First node from where the graph starts
builder.add_edge(START, "assistant")

# Instead of fallback=END, use path_map with an entry for the "END" string:
builder.add_conditional_edges(
    # The node from where this conditional route starts.
    "assistant",
    # The function that returns "verification" or "END".
    route_branch,
    # A dict mapping return-values -> next-nodes
    {
        "verification": "verification",
        "END": END  # map the string "END" to the actual sentinel END
    }
)

# The checkpointer lets the graph persist its state
memory = MemorySaver()
part_1_graph = builder.compile(checkpointer=memory)

# Optionally visualize
part_1_graph.get_graph(xray=True).draw_mermaid_png()

def interactive_chat():
    print("Demo starting... (Type 'quit' to exit)")
    
    # Initialize the chat state
    state = {"messages": []}
    
    # Add logging for initial state
    print("\nInitial state:", state)
    
    # Provide default config
    config = {
        "configurable": {
            "thread_id": "default_thread",
            "checkpoint_ns": "default_namespace",
            "checkpoint_id": "default_checkpoint",
            "passenger_id": "default_passenger"
        }
    }
    
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() == 'quit':
            break

        state["messages"].append(("user", user_input))
        
        try:
            # Log state before invoking graph
            print("\nState before graph:", state)
            
            # Invoke the graph
            result = part_1_graph.invoke(state, config)
            
            # Log raw result
            print("\nRaw result:", result)
            
            state = result
            
            if "messages" in result:
                last_message = result["messages"][-1]
                # Log the type and content of last_message
                print("\nLast message type:", type(last_message))
                print("Last message content:", last_message)
                
                # Handle AIMessage format
                if hasattr(last_message, "content"):
                    print("\nAssistant:", last_message.content)
                # Handle tuple format (role, content)
                elif isinstance(last_message, tuple):
                    print("\nAssistant:", last_message[1])
                # Handle direct string content
                elif isinstance(last_message, str):
                    print("\nAssistant:", last_message)
                # Fallback for any other format
                else:
                    print("\nAssistant:", str(last_message))
        except Exception as e:
            print("\nError:", str(e))
            print("Exception type:", type(e))
            print("Please try again.")

if __name__ == "__main__":
    interactive_chat()