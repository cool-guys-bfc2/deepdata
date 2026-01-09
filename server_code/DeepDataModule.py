import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import requests
import re

@anvil.server.callable
def run(rtext):
  """
    Main AI logic. Processes facts, questions, and mathematical clauses.
    """
  text = rtext.strip().lower()
  if not text:
    return ""

  db = app_tables.database

  # 1. EXTRACT NUMBERS (for math clauses)
  # Finds integers and decimals
  nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)

  # 2. CHECK FOR LEARNED CLAUSES (e.g., 'plus is <x> + <y>')
  # We look for any word in the sentence that matches a 'Name' in our database
  words = text.split()
  for word in words:
    row = db.get(Names=word)
    if row and "<x>" in str(row['Object']):
      expression = str(row['Object'])

      # If we have at least 2 numbers, execute the logic
      if len(nums) >= 2:
        try:
          # Replace placeholders with the found numbers
          # nums[0] is <x>, nums[1] is <y>
          safe_expr = expression.replace("<x>", nums[0]).replace("<y>", nums[1])

          # Safe Eval: No access to system built-ins
          result = eval(safe_expr, {"__builtins__": None}, {})
          return f"the {word} of {nums[0]} and {nums[1]} is {result}"
        except Exception as e:
          return f"error calculating {word}: {str(e)}"

    # 3. SET/VAL LOGIC (is/are)
    # Handles "what is the sun" or "the sun is a star"
  if " is " in text or " are " in text:
    verb = " is " if " is " in text else " are "
    parts = text.split(verb, 1)
    subject = parts[0].replace("what", "").strip()
    description = parts[1].strip()

    # If it's a question (starts with 'what')
    if text.startswith("what"):
      row = db.get(Names=subject)
      if row:
        return f"{subject} {verb} {row['Object']}"
      else:
        return f"i do not know what {subject} {verb} yet"

        # If it's a statement, learn it
    else:
      existing = db.get(Names=subject)
      if not existing:
        db.add_row(ID=str(len(db.search())), Names=subject, Object=description)
      else:
        existing['Object'] = description # Update knowledge
      return f"confirmed: {subject} {verb} {description}"

  return "i heard you, but i do not have a rule for that yet."

@anvil.server.callable
def learnfromurl(url):
  """
    Reads a raw text file from a URL to teach the AI line by line.
    """
  try:
    print(f"--- accessing: {url} ---")
    # Standard 2026 headers to bypass bot-blocks
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code != 200:
      print(f"failed to load. status code: {response.status_code}")
      return

      # Split by sentence-ending markers
    lines = response.text.replace(".", "\n").replace("?", "\n").split("\n")
    learned_count = 0

    for line in lines:
      clean_line = line.strip().lower()
      # Complexity Filter: Only learn clean 'is/are' statements
      if any(v in f" {clean_line} " for v in [" is ", " are "]):
        # Skip long sentences to keep logic simple
        if 3 <= len(clean_line.split()) <= 15:
          run(clean_line)
          print(f"learned: {clean_line}")
          learned_count += 1

    print(f"--- finished. learned {learned_count} statements. ---")
  except Exception as e:
    print(f"url error: {str(e)}")

@anvil.server.callable
def reset_database():
  """Clear all knowledge (Optional utility)."""
  for row in app_tables.database.search():
    row.delete()
  return "database cleared"
