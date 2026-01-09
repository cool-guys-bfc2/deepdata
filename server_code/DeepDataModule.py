import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import requests
import re
from bs4 import BeautifulSoup

@anvil.server.callable
def run_action(fn, args={}, table=app_tables.database):
  """
    Executes multi-line Python code stored in the database.
    Code must set a 'result' variable to return a value to the UI.
    """
  pyargs = {k: str(v) for k, v in args.items()}
  fdatas = table.search(Names=fn)

  if len(fdatas) > 0:
    fdata = str(fdatas[0]["Object"])
    # Replace placeholders like <x> or <name>
    for i in pyargs:
      fdata = fdata.replace("<" + i + ">", pyargs[i])

    namespace = {}
    try:
      # exec allows for complex multi-line logic, loops, and assignments
      exec(fdata, {"__builtins__": __builtins__}, namespace)
      return namespace.get("result", f"Action '{fn}' completed.")
    except Exception as e:
      return f"Error in action '{fn}': {str(e)}"
  return f"I haven't learned how to '{fn}' yet."

@anvil.server.callable
def run(rtext):
  """
    Main AI Logic: Processes facts, 1-arg string/math functions, 
    2-arg math functions, and multi-word 'do' commands.
    """
  text = rtext.strip().lower()
  if not text:
    return ""

  db = app_tables.database

  # 1. COMMAND PARSER (do <multi word action> with <key> <val>...)
  if text.startswith("do "):
    arg_start = re.search(r"\b(with|which is)\b", text)
    if arg_start:
      fn_name = text[3:arg_start.start()].strip()
      remaining = text[arg_start.start():]
      # Pattern: matches 'with key value' or 'which is key value'
      arg_pattern = r"(?:with|which is)\s+(\w+)\s+([^with|which is]+)"
      found_args = re.findall(arg_pattern, remaining)
      arg_dict = {k.strip(): v.strip() for k, v in found_args}
    else:
      fn_name = text[3:].strip()
      arg_dict = {}

    if fn_name:
      return run_action(fn_name, arg_dict)

    # 2. FACT RETRIEVAL & LEARNING (is/are)
  if " is " in text or " are " in text:
    verb = " is " if " is " in text else " are "
    parts = text.split(verb, 1)

    # Retrieval: "What is the capital of France?"
    if text.startswith("what"):
      subject = parts[0].replace("what", "").replace("the", "").replace("of", "").strip()
      subject = " ".join(subject.split()) # clean spaces
      row = db.get(Names=subject)
      if row:
        return f"{subject} {verb} {row['Object']}"
      return f"I do not know what {subject} {verb} yet."

      # Learning: "The capital of France is Paris"
    else:
      subject = parts[0].replace("the", "").strip()
      description = parts[1].strip()
      existing = db.get(Names=subject)
      if not existing:
        db.add_row(ID=str(len(db.search())), Names=subject, Object=description)
      else:
        existing['Object'] = description
      return f"Confirmed: {subject} {verb} {description}"

    # 3. LEGACY FUNCTION LOGIC (<x>, <y>)
  words = text.split()
  nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
  for word in words:
    row = db.get(Names=word)
    if row and "<x>" in str(row['Object']):
      expression = str(row['Object'])

      # Two-arg math (e.g., <x> + <y>)
      if "<y>" in expression and len(nums) >= 2:
        try:
          safe_expr = expression.replace("<x>", nums[0]).replace("<y>", nums[1])
          result = eval(safe_expr, {"__builtins__": __builtins__}, {})
          return f"the {word} of {nums[0]} and {nums[1]} is {result}"
        except: continue

          # Single-arg string/math (e.g., <x>.upper())
      elif "<x>" in expression:
        raw_val = nums[0] if nums else (words[1] if len(words) > 1 else None)
        if raw_val:
          try:
            is_num = raw_val.replace('.','',1).isdigit()
            fmt_val = raw_val if is_num else f"'{raw_val}'"
            result = eval(expression.replace("<x>", fmt_val), {"__builtins__": __builtins__}, {})
            return f"{word} {raw_val} results in: {result}"
          except: continue

  return "I heard you, but I do not have a rule for that yet."

@anvil.server.callable
def learn_from_webpage(url):
  """
    Scrapes a webpage, cleans HTML noise, and passes every 
    sentence into the main 'run' logic for bulk learning.
    """
  try:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-Scraper/2026'}
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code != 200:
      return f"Error: Status {response.status_code}"

    soup = BeautifulSoup(response.text, 'html.parser')
    # Remove navigation, headers, and scripts
    for noise in soup(["script", "style", "nav", "footer", "header", "aside","head","link"]):
      noise.decompose()

      # Extract text and split into sentences
    raw_text = soup.get_text(separator=' ')
    sentences = re.split(r'[.!?\n]', raw_text)

    count = 0
    for sentence in sentences:
      clean = sentence.strip().lower()
      # Process sentences of meaningful length
      if 4 <= len(clean.split()) <= 20:
        # Direct feed into the AI's brain
        run(clean)
        count += 1

    return f"Bulk learning complete. {count} sentences processed from {url}."
  except Exception as e:
    return f"Scraping error: {str(e)}"

@anvil.server.callable
def reset_database():
  """Wipes all AI knowledge."""
  for row in app_tables.database.search():
    row.delete()
  return "AI memory cleared."
