**Greetings**
Step 1:
Caller response: 'Good morning/Afternoon/Evening Sir/Miss/Mdm. My name is <Name of the caller> calling from <bank name> and I would like to speak with <Debtor's Full Name>.'

If Debtor response: 'Yes Speaking' 
    #Proceed to Step 2#
If: Debtor response : 'No, wrong number'
    #Proceed to {script_1}#
If: Debtor response : 'I cannot talk right now or I am in the meeting or can you call me back' 
    #Proceed to {script_3}#

**Verification**
Step 2:
Caller response: 'To ensure I am speaking with the correct person, may I confirm your last 4 digits of your IC number or Date of Birth please?'
If: Debtor response: Reads out 'Last 4 digits IC number or Date of birth'
    Then: Caller response: 'Thank you for the verification this call may be recorded for quality and compliances purposes.' 
    #Proceed to Step 3#
Else-if: Debtor response (Any of below):
	'Why must I read my ic numbers or I cannot read my ic numbers you can check in your system'
        #Proceed to {script_3}
	'You are a scammer or bank is Scammer'
        #Proceed to {script_4}
	'I have fully settled the account long time ago'
        #Proceed to {script_5}
	'I have do not have any account with your bank'
        #Proceed to {script_6}
	'This is a fraud case I have notified your bank'
        #Proceed to {script_7}
	'Keep receiving many calls will lodge a police report'
        #Proceed to {script_8}
	'Keep harassing by calls will lodge a report to central bank  
        #Proceed {script_9}
	'This account is Time barred I do not have to pay'
        #Proceed to {script_10}
	'I will not pay' 
        #Proceed to  {script_11}'
	'I cannot afford to pay'
        #Proceed to {script_13}
	'I am jobless not working'
        #Proceed to {script_13}
	'I am Sick I cannot pay'
        #Proceed to {script_14}


Step 3:
Caller response: 'The reason for this call is to inform you that  your <Product> account formerly from Dbank  is still outstanding and we would like to assist you in working out a payment plan options that might work for you. Would you be open to discussing a plan that fits you.'
If: Debtor response: 'what is my current outstanding balance?.'
    then: Caller response: 'Thank you for your cooperation and your current outstanding balance is  RM<amount> and it could sound huge to you as the debt was outstanding for some time without any payment.  However, we would like to assist you to settle the debt with 2 payment plans options that might work for you.'
If: Debtor response :'Yes I would like to know more about the payment Plan or what is the payment plan'
    then: Caller response: 'The payment plan 1 is a  one-time payment option with substantial  discount of <X%> where you could settle the debt in full for <amount> . This is the fastest way to clear your record and get removed from blacklist as once you have paid the debt we  will issue a release letter and you’ll be removed from the blacklist. This can help improve your financial standing and move forward without restrictions. 
                'The payment plan 2 is a  monthly payment plan for RM<amount> starting with an initial payment of RM<amount>, followed by monthly installment of RM<Amount> over <months>. We will remove your blacklist record only once the account is fully settled.'
If: Debtor’s response: 'Yes I would like to discuss further about the onetime payment or monthly payment or payment plan 1 or payment plan 2. or Yes, I need know more detail about this payment plans.
    then: To proceed to Step 4
If: Debtor’s  response : 'Yes I would like to discuss further about this payment plans, can you please call me back.'
    then: To proceed to Step 5

**Closure**
Step 4:
Caller response: 'Thank you for your cooperation and I will be connecting this call to the Credit Management officer that in charge of your account for further discussion. Please hold the line and at the same time you will receive a SMS notification with the detail of the Person In charge and contact detail to call back if this line is disconnected during the transfer of this call.' 
Step 5: 
If: Caller response: 'We have noted your request for a call back and would like to confirm your preferred date and time for the discussion.' 
    then: Debtor response : 'Can you call back on <Date> and <Time>.'
        then: Caller respnse: 'Thank you for your response and we will schedule a call to you as per your schedule and our Credit Management Officer in charge of your account will call you back on the given date and time and at the same time you will receive a SMS notification with the detail of the Person In charge and contact detail for your reference. Thank you and have nice day.'



After this each script 1-13 has many conditional statement too. Till call is closed in agreement or disagreement
 