from datetime import datetime
from typing import Annotated, TypedDict
from typing_extensions import TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AnyMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.base import RunnableLambda

from langgraph.graph import StateGraph, Graph
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.prebuilt import ToolNode

# Define the state
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

# Create the assistant class
class Assistant:
    def __init__(self, runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            configuration = config.get("configurable", {})
            passenger_id = configuration.get("passenger_id", None)
            state = {**state, "user_info": passenger_id}
            result = self.runnable.invoke(state)
            # Re-prompt if empty response
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

# Initialize LLM
llm = ChatAnthropic(model="claude-3-sonnet-20240229", temperature=1)

# Create the assistant prompt
primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful customer support assistant for Swiss Airlines. "
            "Use the provided tools to search for flights, company policies, and other information to assist the user's queries. "
            "When searching, be persistent. Expand your query bounds if the first search returns no results. "
            "If a search comes up empty, expand your search before giving up."
            "\n\nCurrent user:\n<User>\n{user_info}\n</User>"
            "\nCurrent time: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now)

# Create tool node with error handling
def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }

def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

def tools_condition(state: State):
    """Determines if we should route to tools or end."""
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "END"

# Define the graph
def create_graph(tools):
    builder = StateGraph(State)
    
    # Add nodes
    builder.add_node("assistant", Assistant(primary_assistant_prompt | llm.bind_tools(tools)))
    builder.add_node("tools", create_tool_node_with_fallback(tools))
    builder.add_node("end")  # Add an explicitly named end node for the graph

    # Instead of referencing 'START', make 'assistant' the start node:
    builder.set_start("assistant")
    # And make 'end' the final node:
    builder.set_end("end")

    # Add edges
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
        {
            "tools": "tools",
            "END": "end"
        }
    )
    builder.add_edge("tools", "assistant")
    
    # Compile the graph
    return builder.compile()

# Example usage:
if __name__ == "__main__":
    # Define your tools here
    tools = [
        # Add your tools here
    ]
    
    graph = create_graph(tools)
    
    # Example config
    config = {
        "configurable": {
            "passenger_id": "3442 587242",
            "thread_id": "example_thread"
        }
    }
    
    # Example usage
    response = graph.invoke(
        {"messages": [("user", "What time is my flight?")]},
        config
    )
    print(response)
