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
        If the person confirms their identity (by saying 'yes', 'speaking', or similar confirmation), 
        respond with: "TRANSFER_TO_VERIFICATION"
        If they deny or seem unsure, try to confirm if they are the correct person.
        Be professional and courteous at all times."""
        super().__init__(system_prompt)

    def get_response(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        
        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=150,
                temperature=0.7,
                system=self.system_prompt,
                messages=self.conversation_history
            )
            
            bot_response = message.content[0].text
            # Check if user confirmed identity with common confirmation phrases
            if user_input.lower() in ['yes', 'yes speaking', 'speaking', 'that\'s me', 'this is john', 'i am john']:
                bot_response = "TRANSFER_TO_VERIFICATION"
            
            self.conversation_history.append({"role": "assistant", "content": bot_response})
            return bot_response
            
        except Exception as e:
            return f"An error occurred: {str(e)}"

class VerificationAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a debt verification agent.
        When you first start, say: "Hello, I'm Sarah from our verification department. I'll be assisting you with verifying some details and discussing your account."
        Ask for the last 4 digits of their account number.
        Once the user provides any 4 digits, respond with: "TRANSFER_TO_THANKS"
        Be professional and courteous at all times."""
        super().__init__(system_prompt)

    def get_response(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        
        try:
            message = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=150,
                temperature=0.7,
                system=self.system_prompt,
                messages=self.conversation_history
            )
            
            bot_response = message.content[0].text
            # Check if user provided 4 digits
            if any(word.isdigit() and len(word) == 4 for word in user_input.split()):
                bot_response = "TRANSFER_TO_THANKS"
            
            self.conversation_history.append({"role": "assistant", "content": bot_response})
            return bot_response
            
        except Exception as e:
            return f"An error occurred: {str(e)}"

class ThanksAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a debt collection agent providing account information.
        When you start, say: "Thanks for confirming your identity. I can see your account has an outstanding balance of $2,457.83 which was due on March 15th, 2024. 
        Would you like to discuss payment arrangements?"
        Then proceed to discuss payment options if the user is interested.
        Be professional, understanding, and helpful."""
        super().__init__(system_prompt)

class MultiAgentDebtCollectionBot:
    def __init__(self):
        self.initial_agent = InitialAgent()
        self.verification_agent = VerificationAgent()
        self.thanks_agent = ThanksAgent()
        self.current_agent = self.initial_agent
        self.identity_confirmed = False
        self.verification_complete = False

    def get_response(self, user_input):
        response = self.current_agent.get_response(user_input)
        
        # Check for transfers
        if not self.identity_confirmed and "TRANSFER_TO_VERIFICATION" in response:
            self.identity_confirmed = True
            self.current_agent = self.verification_agent
            return self.verification_agent.get_response("Start verification")
        
        if not self.verification_complete and "TRANSFER_TO_THANKS" in response:
            self.verification_complete = True
            self.current_agent = self.thanks_agent
            return self.thanks_agent.get_response("Start thanks")
        
        return response

    def clear_history(self):
        self.initial_agent.clear_history()
        self.verification_agent.clear_history()
        self.thanks_agent.clear_history()
        self.current_agent = self.initial_agent
        self.identity_confirmed = False
        self.verification_complete = False

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
