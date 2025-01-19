import getpass
import os
from datetime import date, datetime


def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")


_set_env("ANTHROPIC_API_KEY")
_set_env("OPENAI_API_KEY")
#_set_env("TAVILY_API_KEY")
os.environ["TAVILY_API_KEY"] = ""


from typing import Annotated

from typing_extensions import TypedDict

from langgraph.graph.message import AnyMessage, add_messages


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


from langchain_anthropic import ChatAnthropic
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig


class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            configuration = config.get("configurable", {})
            passenger_id = configuration.get("passenger_id", None)
            state = {**state, "user_info": passenger_id}
            result = self.runnable.invoke(state)
            # If the LLM happens to return an empty response, we will re-prompt it
            # for an actual response.
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}


# Haiku is faster and cheaper, but less accurate
# llm = ChatAnthropic(model="claude-3-haiku-20240307")
llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=1)
# You could swap LLMs, though you will likely want to update the prompts when
# doing so!
# from langchain_openai import ChatOpenAI

# llm = ChatOpenAI(model="gpt-4-turbo-preview")

primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful polite debt recovery agent, greet the user with 'Good morning/Afternoon/Evening Sir/Miss/Mdm. My name is <Name of the caller> calling from <bank name> and I would like to speak with <Debtor's Full Name>.' "
            "\nCurrent time: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now)

part_1_tools = [
    
]
part_1_assistant_runnable = primary_assistant_prompt | llm.bind_tools(part_1_tools)

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import tools_condition

builder = StateGraph(State)


# Define nodes: these do the work
builder.add_node("assistant", Assistant(part_1_assistant_runnable))
#builder.add_node("tools", create_tool_node_with_fallback(part_1_tools))
# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
'''builder.add_conditional_edges(
    "assistant",
    tools_condition,
)'''
#builder.add_edge("tools", "assistant")

# The checkpointer lets the graph persist its state
# this is a complete memory for the entire graph.
memory = MemorySaver()
part_1_graph = builder.compile(checkpointer=memory)

part_1_graph.get_graph(xray=True).draw_mermaid_png()

def interactive_chat():
    print("Demo starting... (Type 'quit' to exit)")
    
    # Initialize the chat state
    state = {"messages": []}
    
    # Create a configuration with required checkpointer keys
    config = {
        "configurable": {
            "thread_id": "default_thread",
            "checkpoint_ns": "default_namespace",
            "checkpoint_id": "default_checkpoint",
            "passenger_id": "default_passenger"  # Added passenger_id for tools
        }
    }
    
    while True:
        # Get user input
        user_input = input("\nYou: ").strip()
        
        # Check for quit command
        if user_input.lower() == 'quit':
            break
        
        # Add user message to state
        state["messages"].append(("user", user_input))
        
        try:
            # Get response from graph with config
            result = part_1_graph.invoke(state, config)
            state = result
            
            # Extract and print assistant's response
            if "messages" in result:
                last_message = result["messages"][-1]
                # Handle different message formats
                if hasattr(last_message, "content"):
                    # If it's an AIMessage object
                    print("\nAssistant:", last_message.content)
                elif isinstance(last_message, tuple):
                    # If it's a tuple of (role, content)
                    print("\nAssistant:", last_message[1])
                else:
                    print("\nAssistant:", str(last_message))
            
        except Exception as e:
            print("\nError:", str(e))
            print("Please try again.")

if __name__ == "__main__":
    interactive_chat()

