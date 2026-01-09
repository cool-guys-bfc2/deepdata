from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Form1(Form1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run before the form opens.

  @handle("submit", "click")
  def submit_click(self, **event_args):
    """This method is called when the button is clicked"""
    if "https://" not in self.text_area_1.text:
      self.label_1.text+="\n"+anvil.server.call('run',self.text_area_1.text)
    else:
      anvil.server.call('learnfromurl',self.text_area_1.text)