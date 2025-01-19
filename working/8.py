import anthropic
import os
from datetime import datetime

class BaseAgent:
    def __init__(self, system_prompt):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.system_prompt = system_prompt
        self.conversation_history = []

    def get_response(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        
        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=150,
                temperature=0.7,
                system=self.system_prompt,
                messages=[
                    {"role": m["role"], "content": m["content"]} 
                    for m in self.conversation_history if m["role"] == "user"
                ]
            )
            
            bot_response = message.content[0].text
            self.conversation_history.append({"role": "assistant", "content": bot_response})
            return bot_response
            
        except Exception as e:
            return f"An error occurred: {str(e)}"

    def clear_history(self):
        self.conversation_history = []

class InitialAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a debt collection agent making initial contact. 
        For your first message, begin with: "Good morning/Afternoon/Evening Sir/Miss/Mdm. My name is Alex calling from Credence Bank and I would like to speak with John Doe."
        Your only role is to verify if you're speaking with the correct person.
        If the person confirms their identity in any way, respond with: "TRANSFER_TO_VERIFICATION"
        If they deny or seem unsure respond with: "TRANSFER_TO_SORRY"
        Be professional and courteous at all times. Stick to the Script as much as possible"""
        super().__init__(system_prompt)
        self.confirmation_attempts = 0

    def get_response(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        
        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=150,
                temperature=0.2,
                system=self.system_prompt,
                messages=self.conversation_history
            )
            
            bot_response = message.content[0].text
            
            # Let the LLM determine if identity is confirmed through its response
            '''if "TRANSFER_TO_VERIFICATION" not in bot_response:
                self.confirmation_attempts += 1
                if self.confirmation_attempts >= 2:
                    bot_response = "TRANSFER_TO_SORRY"'''
            
            self.conversation_history.append({"role": "assistant", "content": bot_response})
            return bot_response
            
        except Exception as e:
            return f"An error occurred: {str(e)}"

class VerificationAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a verification agent.
        When you first start, say: "To ensure I am speaking with the correct person, may I confirm your last 4 digits of your IC number or Date of Birth please?"
        Once the user provides any 4 digits or a date of birth, respond with: "TRANSFER_TO_DISCUSSION"
        If they fail to provide proper verification information, respond with: "TRANSFER_TO_SORRY"
        Be professional and courteous at all times. Stick to the Script as much as possible"""
        super().__init__(system_prompt)

    def get_response(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        
        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=150,
                temperature=0.2,
                system=self.system_prompt,
                messages=self.conversation_history
            )
            
            bot_response = message.content[0].text
            self.conversation_history.append({"role": "assistant", "content": bot_response})
            return bot_response
            
        except Exception as e:
            return f"An error occurred: {str(e)}"

class DiscussionAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a debt collection agent providing account information.
        When you start, say: "Thank you for the verification this call may be recorded for quality and compliances purposes. The reason for this call is to inform you that  your <Product> account formerly from Dbank  is still outstanding and we would like to assist you in working out a payment plan options that might work for you. Would you be open to discussing a plan that fits you."
        Be professional, understanding, and helpful. Stick to the Script as much as possible"""
        super().__init__(system_prompt)

class SorryAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a debt collection agent handling unexpected scenarios.
        When you start, say: "I apologize, but I haven't been programmed to handle this situation yet. 
        Please contact our customer service at 1-800-XXX-XXXX during business hours. Have a good day!"
        End the conversation after delivering thishi message. Stick to the Script as much as possible"""
        super().__init__(system_prompt)

class MultiAgentDebtCollectionBot:
    def __init__(self):
        self.initial_agent = InitialAgent()
        self.verification_agent = VerificationAgent()
        self.discussion_agent = DiscussionAgent()
        self.sorry_agent = SorryAgent()
        self.current_agent = self.initial_agent
        self.identity_confirmed = False
        self.verification_complete = False
        self.conversation_ended = False

    def get_response(self, user_input):
        if self.conversation_ended:
            return "The conversation has ended. Type 'clear' to start a new conversation."
            
        response = self.current_agent.get_response(user_input)
        
        # Check for transfers
        if not self.identity_confirmed and "TRANSFER_TO_VERIFICATION" in response:
            self.identity_confirmed = True
            self.current_agent = self.verification_agent
            return self.verification_agent.get_response("Start verification")
        
        if not self.verification_complete and "TRANSFER_TO_DISCUSSION" in response:
            self.verification_complete = True
            self.current_agent = self.discussion_agent
            return self.discussion_agent.get_response("Start discussion")

        if "TRANSFER_TO_SORRY" in response:
            self.current_agent = self.sorry_agent
            self.conversation_ended = True
            return self.sorry_agent.get_response("Start sorry")
            
        return response

    def clear_history(self):
        self.initial_agent.clear_history()
        self.verification_agent.clear_history()
        self.discussion_agent.clear_history()
        self.sorry_agent.clear_history()
        self.current_agent = self.initial_agent
        self.identity_confirmed = False
        self.verification_complete = False
        self.conversation_ended = False

def main():
    # Initialize the multi-agent bot
    bot = MultiAgentDebtCollectionBot()
    
    print("Demo begins, type hi or hello to start")
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() == 'quit':
            print("Debt Collection Bot: Goodbye! Have a great day!")
            break
        
        if user_input.lower() == 'clear':
            bot.clear_history()
            print("Debt Collection Bot: Conversation history cleared. How can I help you?")
            continue
        
        response = bot.get_response(user_input)
        print(f"Debt Collection Bot: {response}")

if __name__ == "__main__":
    main()
