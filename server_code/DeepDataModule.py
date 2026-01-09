import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import requests
import re

@anvil.server.callable
def run(rtext):
  """
    2026 AI Logic: Handles facts, 1-arg string/math functions, 
    and 2-arg math functions.
    """
  text = rtext.strip().lower()
  if not text:
    return ""

  db = app_tables.database
  words = text.split()

  # 1. EXTRACT DATA
  # Find all numbers (floats or ints)
  nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
  # Find words that aren't grammar keywords to use as string inputs
  potential_inputs = [w for w in words if w not in ["is", "are", "what", "the", "a", "an"]]

  # 2. CHECK FOR FUNCTIONS (<x>, <y>)
  for word in words:
    row = db.get(Names=word)
    if row and "<x>" in str(row['Object']):
      expression = str(row['Object'])

      # --- Two-Argument Case (e.g., 'plus is <x> + <y>') ---
      if "<y>" in expression and len(nums) >= 2:
        try:
          safe_expr = expression.replace("<x>", nums[0]).replace("<y>", nums[1])
          # We allow builtins here so math and string methods work
          result = eval(safe_expr, {"__builtins__": __builtins__}, {})
          return f"the {word} of {nums[0]} and {nums[1]} is {result}"
        except Exception as e:
          return f"math error: {str(e)}"

          # --- Single-Argument Case (e.g., 'reverse is <x>[::-1]') ---
      elif "<x>" in expression:
        # Use a number if available; otherwise use the first word that isn't the command
        raw_val = None
        if nums:
          raw_val = nums[0]
        else:
          # Filter out the function name itself from inputs
          args = [i for i in potential_inputs if i != word]
          if args:
            raw_val = args[0]

        if raw_val:
          try:
            # If input is text, wrap it in quotes so eval treats it as a string
            is_num = raw_val.replace('.','',1).isdigit()
            formatted_val = raw_val if is_num else f"'{raw_val}'"

            safe_expr = expression.replace("<x>", formatted_val)
            # Fix: Don't set builtins to None; required for slicing/methods
            result = eval(safe_expr, {"__builtins__": __builtins__}, {})
            return f"{word} {raw_val} results in: {result}"
          except Exception as e:
            return f"error in {word}: {str(e)}"

    # 3. FACT LEARNING & RETRIEVAL (is/are)
  if " is " in text or " are " in text:
    verb = " is " if " is " in text else " are "
    parts = text.split(verb, 1)
    # Clean subject: "what is the sun" -> "sun"
    subject = parts[0].replace("what", "").replace("the", "").strip()
    subject= subject.replace("of","").replace("  "," ")
    description = parts[1].strip()

    if text.startswith("what"):
      row = db.get(Names=subject)
      if row:
        return f"{subject} {verb} {row['Object']}"
      return f"i do not know what {subject} {verb} yet"
    else:
      existing = db.get(Names=subject)
      if not existing:
        db.add_row(ID=str(len(db.search())), Names=subject, Object=description)
      else:
        existing['Object'] = description 
      return f"learned: {subject} {verb} {description}"

  return "i heard you, but i do not have a rule for that yet."

@anvil.server.callable
def learnfromurl(url):
  """Fetches text from a URL and learns 'is/are' facts."""
  try:
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
      return f"Error: Status {response.status_code}"

    lines = response.text.replace(".", "\n").replace("?", "\n").split("\n")
    count = 0
    for line in lines:
      clean = line.strip().lower()
      if any(v in f" {clean} " for v in [" is ", " are "]):
        if 3 <= len(clean.split()) <= 15:
          run(clean)
          count += 1
    return f"Finished. Learned {count} statements."
  except Exception as e:
    return f"URL Error: {str(e)}"

@anvil.server.callable
def reset_database():
  """Wipes the knowledge base."""
  for row in app_tables.database.search():
    row.delete()
  return "Database cleared."
