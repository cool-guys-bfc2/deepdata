from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
import random
from anvil.tables import app_tables

class Form1(Form1Template):
  def __init__(self, **properties):
    # Set up form components and initial state
    self.init_components(**properties)

    # Initialize the Conversation ID as None 
    # (The server will generate one on the first call)
    self.conversation_id = random.randint(100,999)

  @handle("button_send", "click")
  def button_send_click(self, **event_args):
    """This method is called when the send button is clicked."""
    user_input = self.text_box_input.text

    if not user_input:
      return
    # 1. Clear input box immediately for better UX
    self.text_box_input.text = ""
    if user_input.startswith("http://") or user_input.startswith("https://"):
      res=""
      if user_input.startswith('http://en.wikipedia.org/wiki/') or user_input.startswith('https://en.wikipedia.org/wiki/'):
        res=anvil.server.call('learn_from_wikipedia',user_input)
      else:
        res=anvil.server.call('learn_from_url',user_input)
      self.label_1.text+="\nYou: "+user_input
      self.label_1.text+="\nAI: "+res
      return
        
    # 2. Add user message to UI (optional: create a custom label or row)
    print(f"User: {user_input}") 
    self.label_1.text+="\nYou: "+user_input
    # 3. Call the AI Server Module
    # We pass our current conversation_id so the AI remembers us
    try:
      result = anvil.server.call('run', user_input, self.conversation_id)

      # 4. Update the Conversation ID and display response
      # The server returns a dict: {"response": str, "id": int}
      if isinstance(result,dict):
        self.conversation_id = result['id']
        ai_response = result['response']
      else:
        ai_response=result
        if not self.conversation_id:
          self.conversation_id=random.randint(100,999)

      # Display the AI's response in a Label or Alert
      # In 2026, using notification or adding to a chat list is standard
      Notification(f"AI (ID {str(self.conversation_id)}): {ai_response}").show()
      self.label_1.text+="\nAi("+str(self.conversation_id)+"): "+ai_response
    except Exception as e:
      alert(f"An error occurred: {str(e)}")

  def text_box_input_pressed_enter(self, **event_args):
    """Allows user to press 'Enter' instead of clicking the button."""
    self.button_send_click()
