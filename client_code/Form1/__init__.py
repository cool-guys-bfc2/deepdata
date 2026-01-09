import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import requests
import re
from bs4 import BeautifulSoup

def get_levenshtein(s1, s2):
  """Calculates letter-difference rating (Lower = Closer match)."""
  if len(s1) < len(s2): return get_levenshtein(s2, s1)
  if len(s2) == 0: return len(s1)
  previous_row = range(len(s2) + 1)
  for i, c1 in enumerate(s1):
    current_row = [i + 1]
    for j, c2 in enumerate(s2):
      insertions = previous_row[j + 1] + 1
      deletions = current_row[j] + 1
      substitutions = previous_row[j] + (c1 != c2)
      current_row.append(min(insertions, deletions, substitutions))
    previous_row = current_row
  return previous_row[-1]

@anvil.server.callable
def run(rtext):
  """
    Primary Entry Point. Handles:
    1. Pending autocorrect confirmations
    2. Spell-checking logic (ignoring numbers/symbols)
    3. Delegation to run_logic
    """
  text = rtext.strip().lower()
  if not text: return ""

    # A. SESSION STATE: Check if we are waiting for a Yes/No to a correction
    # Note: Requires a table 'session' with columns ['key', 'value']
  state = app_tables.session.get(key="pending_correction")
  if state and state['value']:
    pending_data = eval(state['value']) # Dictionary: {'original': str, 'suggested': str}
    if text in ["yes", "y", "yeah", "correct"]:
      actual_text = pending_data['suggested']
      state['value'] = None
      return f"Confirmed. Processing: {actual_text}\n" + run_logic(actual_text)
    elif text in ["no", "n", "nope"]:
      actual_text = pending_data['original']
      state['value'] = None
      return f"Proceeding with original: {actual_text}\n" + run_logic(actual_text)
    else:
      return f"I'm waiting for a 'yes' or 'no'. Did you mean: '{pending_data['suggested']}'?"

    # B. AUTOCORRECT: Only targets alphabetic words
  words = text.split()
  corrected_words = []
  correction_triggered = False

  for word in words:
    # Check if it's a plain word (no numbers/symbols) and not in our dict
    if word.isalpha() and not app_tables.dictionary.get(word=word):
      best_match = None
      lowest_dist = 3 # Max letters allowed to be different

      for entry in app_tables.dictionary.search():
        dist = get_levenshtein(word, entry['word'])
        if dist < lowest_dist:
          lowest_dist = dist
          best_match = entry['word']

      if best_match:
        corrected_words.append(best_match)
        correction_triggered = True
        continue
    corrected_words.append(word)

  if correction_triggered:
    suggested_text = " ".join(corrected_words)
    # Store in session and wait for next call
    state_val = {'original': text, 'suggested': suggested_text}
    if state: state['value'] = str(state_val)
    else: app_tables.session.add_row(key="pending_correction", value=str(state_val))
    return f"Did you mean: '{suggested_text}'?"

  return run_logic(text)

@anvil.server.callable
def run_action(fn, args={}, table=app_tables.database):
  """
    Executes multi-line Python code. 
    If missing data is needed, this function provides the real-time value.
    """
  pyargs = {k: str(v) for k, v in args.items()}
  fdatas = table.search(Names=fn)

  if len(fdatas) > 0:
    fdata = str(fdatas[0]["Object"])
    for i in pyargs:
      fdata = fdata.replace("<" + i + ">", pyargs[i])

    namespace = {}
    try:
      exec(fdata, {"__builtins__": __builtins__}, namespace)
      # Code must define 'result' to return a value
      return namespace.get("result", f"Action {fn} finished.")
    except Exception as e:
      return f"Error in {fn}: {str(e)}"
  return f"Action '{fn}' not found."

def run_logic(text):
  """The AI's processing core."""
  db = app_tables.database

  # 1. DYNAMIC FACT RETRIEVAL
  if text.startswith("what is"):
    subject = text.replace("what is", "").replace("the", "").replace("of", "").strip()
    row = db.get(Names=subject)
    if row:
      stored_val = str(row['Object'])
      # Check if the 'fact' is actually an Action Name (Missing Data Resolver)
      action_exists = db.get(Names=stored_val)
      if action_exists and "<" not in stored_val:
        return run_action(stored_val, {})
      return f"{subject} is {stored_val}"

    # 2. DO ACTION COMMANDS
  if text.startswith("do "):
    arg_match = re.search(r"\b(with|which is)\b", text)
    if arg_match:
      fn_name = text[3:arg_match.start()].strip()
      # ... (Argument parsing logic as previously established)
      return run_action(fn_name, {}) 
    return run_action(text[3:].strip(), {})

    # 3. FACT LEARNING
  if " is " in text:
    parts = text.split(" is ", 1)
    subj, obj = parts[0].strip(), parts[1].strip()
    db.add_row(Names=subj, Object=obj)
    return f"Confirmed: {subj} is {obj}"

  return "I understood the words, but I have no rule for that command yet."

@anvil.server.callable
def learn_from_webpage(url):
  """Scrapes a URL and feeds sentences into the 'run' function."""
  try:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-Core/2026'}
    res = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, 'html.parser')
    for s in soup(["script", "style", "nav", "footer"]): s.decompose()

    sentences = re.split(r'[.!?\n]', soup.get_text(separator=' '))
    count = 0
    for sent in sentences:
      clean = sent.strip().lower()
      if 5 <= len(clean.split()) <= 15:
        run_logic(clean) # Direct to logic to avoid autocorrect loops during scrape
        count += 1
    return f"Learned {count} items from {url}."
  except Exception as e:
    return f"Scrape error: {str(e)}"
