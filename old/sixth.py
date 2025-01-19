from typing import Annotated, TypedDict, Union
from datetime import datetime
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import AnyMessage, add_messages

# Define the possible states
class BotState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    current_step: str
    verified: bool
    debtor_info: dict
    appointment_details: dict

# Initialize Claude 3.5 Sonnet
llm = ChatAnthropic(model="claude-3-sonnet-20240229")

class GreetingNode:
    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a debt collection agent. Use exactly this greeting:
            'Good morning/Afternoon/Evening Sir/Miss/Mdm. My name is {caller_name} calling from {bank_name} 
            and I would like to speak with {debtor_name}.'"""),
            ("human", "{input}")
        ])
        self.chain = self.prompt | llm

    def __call__(self, state: BotState, config: RunnableConfig):
        print(f"DEBUG: GreetingNode called with state: {state}")
        response = self.chain.invoke({
            "input": state["messages"][-1].content,
            "caller_name": state["debtor_info"]["caller_name"],
            "bank_name": state["debtor_info"]["bank_name"],
            "debtor_name": state["debtor_info"]["name"]
        })
        print(f"DEBUG: GreetingNode response: {response}")
        new_state = state.copy()
        new_state["messages"] = state["messages"] + [response]  # Append to message history
        print(f"DEBUG: GreetingNode returning state: {new_state}")
        return new_state

class VerificationNode:
    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are verifying the debtor's identity. Use exactly this script:
            'To ensure I am speaking with the correct person, may I confirm your last 4 digits of your IC number 
            or Date of Birth please?'
            
            If they provide either the IC or DOB, respond:
            'Thank you for the verification this call may be recorded for quality and compliances purposes.'
            
            Then proceed to discussion. If verification fails, proceed to closure."""),
            ("human", "{input}")
        ])
        self.chain = self.prompt | llm

    def __call__(self, state: BotState, config: RunnableConfig):
        response = self.chain.invoke({
            "input": state["messages"][-1].content
        })
        new_state = state.copy()
        new_state["messages"] = [response]
        
        # Verify if provided info matches stored info
        user_input = state["messages"][-1].content.lower()
        if (state["debtor_info"]["ic_last_4"] in user_input or 
            state["debtor_info"]["dob"] in user_input):
            new_state["verified"] = True
        
        return new_state

class DiscussionNode:
    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are discussing the debt. Use exactly this script:
            'The reason for this call is to inform you that your {product} account formerly from Dbank 
            is still outstanding and we would like to assist you in working out a payment plan options 
            that might work for you. Would you be open to discussing a plan that fits you.'
            
            If they ask about balance, respond:
            'Thank you for your cooperation and your current outstanding balance is RM{amount} and it 
            could sound huge to you as the debt was outstanding for some time without any payment. 
            However, we would like to assist you to settle the debt with 2 payment plans options that 
            might work for you.'"""),
            ("human", "{input}")
        ])
        self.chain = self.prompt | llm

    def __call__(self, state: BotState, config: RunnableConfig):
        response = self.chain.invoke({
            "input": state["messages"][-1].content,
            "product": state["debtor_info"]["product"],
            "amount": state["debtor_info"]["amount"]
        })
        new_state = state.copy()
        new_state["messages"] = [response]
        return new_state

class ClosureNode:
    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Use exactly this closure script:
            'Thank you for your cooperation and I will be connecting this call to the Credit Management 
            officer that in charge of your account for further discussion. Please hold the line and at 
            the same time you will receive a SMS notification with the detail of the Person In charge 
            and contact detail to call back if this line is disconnected during the transfer of this call.'"""),
            ("human", "{input}")
        ])
        self.chain = self.prompt | llm

    def __call__(self, state: BotState, config: RunnableConfig):
        response = self.chain.invoke({
            "input": state["messages"][-1].content
        })
        new_state = state.copy()
        new_state["messages"] = [response]
        new_state["current_step"] = "booking"
        return new_state

class BookingNode:
    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """Use exactly this booking script:
            'We have noted your request for a call back and would like to confirm your preferred date 
            and time for the discussion.'
            
            If they provide date and time, respond:
            'Thank you for your response and we will schedule a call to you as per your schedule and 
            our Credit Management Officer in charge of your account will call you back on the given 
            date and time and at the same time you will receive a SMS notification with the detail 
            of the Person In charge and contact detail for your reference. Thank you and have nice day.'"""),
            ("human", "{input}")
        ])
        self.chain = self.prompt | llm

    def __call__(self, state: BotState, config: RunnableConfig):
        response = self.chain.invoke({
            "input": state["messages"][-1].content
        })
        new_state = state.copy()
        new_state["messages"] = [response]
        
        # Check if appointment details were provided
        if self._extract_appointment_details(state["messages"][-1].content):
            # Store appointment details and mark for end
            new_state["appointment_details"] = {"scheduled": True}
            new_state["current_step"] = "end"
        
        return new_state

    def _extract_appointment_details(self, message: str) -> bool:
        # Simple check for date/time mentions
        time_indicators = ["am", "pm", "tomorrow", "today", "next"]
        return any(indicator in message.lower() for indicator in time_indicators)

def create_debt_collection_graph():
    print("DEBUG: Creating graph...")
    workflow = StateGraph(BotState)
    
    # Add nodes
    workflow.add_node("greeting", GreetingNode())
    workflow.add_node("verification", VerificationNode())
    workflow.add_node("discussion", DiscussionNode())
    workflow.add_node("closure", ClosureNode())
    workflow.add_node("booking", BookingNode())
    
    # Set entry point
    workflow.set_entry_point("greeting")
    print("DEBUG: Added nodes and set entry point")
    
    # Add edges with conditions
    workflow.add_conditional_edges(
        "greeting",
        lambda x: print(f"DEBUG: Greeting edge condition input: {x}") or 
                 "verification" if any(word in x["messages"][-1].content.lower() 
                                     for word in ["yes", "speaking", "this is"]) else "closure"
    )
    
    workflow.add_conditional_edges(
        "verification",
        lambda x: print(f"DEBUG: Verification edge condition input: {x}") or
                 "discussion" if x["verified"] else "closure"
    )
    
    workflow.add_conditional_edges(
        "discussion",
        lambda x: print(f"DEBUG: Discussion edge condition input: {x}") or
                 "closure" if any(word in x["messages"][-1].content.lower() 
                                 for word in ["no", "later", "not interested"]) else "discussion"
    )
    
    workflow.add_edge("closure", "booking")
    
    workflow.add_conditional_edges(
        "booking",
        lambda x: print(f"DEBUG: Booking edge condition input: {x}") or
                 END if x["current_step"] == "end" else "booking"
    )
    
    print("DEBUG: Added all edges")
    return workflow.compile()

def initialize_chat():
    return {
        "messages": [],  # Empty list to store message history
        "current_step": "greeting",
        "verified": False,
        "debtor_info": {
            "name": "John Doe",
            "ic_last_4": "1234",
            "dob": "1990-01-01",
            "product": "Credit Card",
            "amount": "10,000",
            "caller_name": "Alex",
            "bank_name": "ABC Bank"
        },
        "appointment_details": {}
    }

def run_interactive_bot():
    print("Starting Debt Collection Bot...")
    print("Bot: Hello! Starting conversation...\n")
    print("DEBUG: Initializing graph and state...")
    
    graph = create_debt_collection_graph()
    state = initialize_chat()
    print(f"DEBUG: Initial state: {state}")
    
    while True:
        try:
            # Get user input
            user_input = input("You: ")
            print(f"\nDEBUG: Received user input: {user_input}")
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\nBot: Thank you for your time. Goodbye!")
                break
            
            # Update state with user's message and maintain message history
            current_state = state.copy()
            current_state["messages"].append(HumanMessage(content=user_input))
            print(f"DEBUG: Current state before graph.invoke: {current_state}")
            
            # Get bot's response
            print("DEBUG: Calling graph.invoke...")
            response = graph.invoke(current_state)
            print(f"DEBUG: Graph response: {response}")
            
            # Update state with bot's response
            state = response
            
            # Print bot's response (get the last message)
            if state["messages"] and isinstance(state["messages"][-1], AIMessage):
                print(f"\nBot: {state['messages'][-1].content}\n")
            
            # Check if conversation has ended
            if state.get("current_step") == "end":
                print("\nBot: Conversation ended. Thank you for your time!")
                break
                
        except Exception as e:
            print(f"\nDEBUG: Error occurred: {str(e)}")
            print(f"DEBUG: Error type: {type(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            print("Bot: I apologize for the error. Let's start over.\n")
            state = initialize_chat()

if __name__ == "__main__":
    run_interactive_bot()
