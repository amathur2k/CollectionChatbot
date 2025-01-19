import anthropic
import os
from datetime import datetime
#MODEL_ID = "claude-3-5-haiku-latest"
MODEL_ID = "claude-3-5-sonnet-latest"

class BaseAgent:
    def __init__(self, system_prompt):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.system_prompt = system_prompt
        self.conversation_history = []

    def get_response(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        
        try:
            message = self.client.messages.create(
                model=f"{MODEL_ID}",
                max_tokens=150,
                temperature=0.2,
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
                model=f"{MODEL_ID}",
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
                model=f"{MODEL_ID}",
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
        IF THIS IS YOUR FIRST MESSAGE IN THE CONVERSATION:
        Say: "Thank you for the verification this call may be recorded for quality and compliances purposes. The reason for this call is to inform you that your <Product> account formerly from Dbank is still outstanding and we would like to assist you in working out a payment plan options that might work for you. Would you be open to discussing a plan that fits you."
        
        FOR ALL SUBSEQUENT MESSAGES:
        If the user asks about their current outstanding balance or similar questions about amount owed:
        Respond ONLY with: "Thank you for your cooperation and your current outstanding balance is RM<amount> and it could sound huge to you as the debt was outstanding for some time without any payment. However, we would like to assist you to settle the debt with 2 payment plans options that might work for you."

        If the user asks to know about payment plans:
        Respond ONLY with: "The payment plan 1 is a one-time payment option with substantial discount of <X%> where you could settle the debt in full for <amount>. This is the fastest way to clear your record and get removed from blacklist as once you have paid the debt we will issue a release letter and you'll be removed from the blacklist. This can help improve your financial standing and move forward without restrictions. The payment plan 2 is a monthly payment plan for RM<amount> starting with an initial payment of RM<amount>, followed by monthly installment of RM<Amount> over <months>. We will remove your blacklist record only once the account is fully settled."

        If the user expresses any interest in either of the payment plans:
        Respond ONLY with: "TRANSFER_TO_CLOSURE"

        If the user requests a callback or wants to discuss the plans later or at a different time:
        Respond ONLY with: "TRANSFER_TO_APPOINTMENT"
        
        Be professional, understanding, and helpful. Stick to the Script as much as possible"""
        super().__init__(system_prompt)
        self.initial_greeting_sent = False

    def get_response(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        
        try:
            context_prompt = "THIS IS YOUR FIRST MESSAGE" if not self.initial_greeting_sent else "THIS IS A FOLLOW-UP MESSAGE"
            message = self.client.messages.create(
                model=f"{MODEL_ID}",
                max_tokens=150,
                temperature=0.2,
                system=f"{self.system_prompt}\n{context_prompt}",
                messages=self.conversation_history
            )
            
            bot_response = message.content[0].text
            self.conversation_history.append({"role": "assistant", "content": bot_response})
            
            if not self.initial_greeting_sent:
                self.initial_greeting_sent = True
                
            return bot_response
            
        except Exception as e:
            return f"An error occurred: {str(e)}"

class SorryAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a debt collection agent handling unexpected scenarios.
        When you start, say: "I apologize, but I haven't been programmed to handle this situation yet. 
        Please contact our customer service at 1-800-XXX-XXXX during business hours. Have a good day!"
        End the conversation after delivering thishi message. Stick to the Script as much as possible"""
        super().__init__(system_prompt)

class ClosureAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a debt collection agent handling call closure.
        When you start, say: "Thank you for your cooperation and I will be connecting this call to the Credit Management officer that in charge of your account for further discussion. Please hold the line and at the same time you will receive a SMS notification with the detail of the Person In charge and contact detail to call back if this line is disconnected during the transfer of this call."
        Stick to the Script exactly as written."""
        super().__init__(system_prompt)

class AppointmentBookingAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are a debt collection agent handling appointment scheduling.
        When you first start, say: "We have noted your request for a call back and would like to confirm your preferred date and time for the discussion."
        
        After the user provides any date/time information:
        Respond ONLY with: "Thank you for your response and we will schedule a call to you as per your schedule and our Credit Management Officer in charge of your account will call you back on the given date and time and at the same time you will receive a SMS notification with the detail of the Person In charge and contact detail for your reference. Thank you and have nice day."
        
        Stick to the Script exactly as written."""
        super().__init__(system_prompt)
        self.initial_request_sent = False

    def get_response(self, user_input):
        self.conversation_history.append({"role": "user", "content": user_input})
        
        try:
            context_prompt = "THIS IS YOUR FIRST MESSAGE" if not self.initial_request_sent else "THIS IS A FOLLOW-UP MESSAGE"
            message = self.client.messages.create(
                model=f"{MODEL_ID}",
                max_tokens=150,
                temperature=0.2,
                system=f"{self.system_prompt}\n{context_prompt}",
                messages=self.conversation_history
            )
            
            bot_response = message.content[0].text
            self.conversation_history.append({"role": "assistant", "content": bot_response})
            
            if not self.initial_request_sent:
                self.initial_request_sent = True
                
            return bot_response
            
        except Exception as e:
            return f"An error occurred: {str(e)}"

class MultiAgentDebtCollectionBot:
    def __init__(self):
        self.initial_agent = InitialAgent()
        self.verification_agent = VerificationAgent()
        self.discussion_agent = DiscussionAgent()
        self.sorry_agent = SorryAgent()
        self.closure_agent = ClosureAgent()
        self.appointment_booking_agent = AppointmentBookingAgent()
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
            
        if "TRANSFER_TO_CLOSURE" in response:
            self.current_agent = self.closure_agent
            self.conversation_ended = True
            return self.closure_agent.get_response("Start closure")
            
        if "TRANSFER_TO_APPOINTMENT" in response:
            self.current_agent = self.appointment_booking_agent
            return self.appointment_booking_agent.get_response("Start appointment")
            
        return response

    def clear_history(self):
        self.initial_agent.clear_history()
        self.verification_agent.clear_history()
        self.discussion_agent.clear_history()
        self.sorry_agent.clear_history()
        self.closure_agent.clear_history()
        self.appointment_booking_agent.clear_history()
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
