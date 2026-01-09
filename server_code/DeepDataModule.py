import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from anvil.server import callable # Explicit import to fix the AttributeError
import requests
import re
import random
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
DICTIONARY_URL = "raw.githubusercontent.com"
cached_dict = set()

def get_dictionary():
  """Fetches and caches the English word list from the provided URL."""
  global cached_dict
  if not cached_dict:
    try:
      headers = {'User-Agent': 'AI-Core-2026'}
      res = requests.get(DICTIONARY_URL, headers=headers, timeout=15)
      if res.status_code == 200:
        cached_dict = {w.strip().lower() for w in res.text.splitlines() if w.strip()}
    except Exception as e:
      print(f"Dictionary Error: {e}")
  return cached_dict

def get_levenshtein(s1, s2):
  """Calculates the edit distance rating between two words."""
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

def generate_unique_3digit_id():
  """Generates a unique ID (100-999). Clears 10 oldest rows if pool is full."""
  used_ids = {r['id'] for r in app_tables.session.search()}
  all_possible = set(range(100, 1000))
  available_ids = list(all_possible - used_ids)

  if not available_ids:
    # Delete 10 oldest rows to free up space
    old_rows = list(app_tables.session.search())[:10]
    for row in old_rows:
      row.delete()
    used_ids = {r['id'] for r in app_tables.session.search()}
    available_ids = list(all_possible - used_ids)

  return random.choice(available_ids)

@callable
def run(rtext, conversation_id=None):
  """Entry Point. Handles Autocorrect and logic delegation."""
  if conversation_id is None:
    conversation_id = generate_unique_3digit_id()

  text = rtext.strip().lower()
  if not text: return {"response": "", "id": conversation_id}

    # 1. SESSION STATE: Check for Yes/No correction
  state = app_tables.session.get(id=conversation_id, key="pending_correction")
  if state and state['value']:
    pending_data = eval(state['value'])
    if text in ["yes", "y", "yeah", "correct"]:
      actual_text = pending_data['suggested']
      state.delete()
      return {"response": f"Confirmed. Processing: {actual_text}\n" + run_logic(actual_text), "id": conversation_id}
    elif text in ["no", "n", "nope"]:
      actual_text = pending_data['original']
      state.delete()
      return {"response": f"Proceeding with original: {actual_text}\n" + run_logic(actual_text), "id": conversation_id}
    else:
      return {"response": f"Did you mean: '{pending_data['suggested']}'? Please say yes or no.", "id": conversation_id}

    # 2. AUTOCORRECT: Only words (no numbers/symbols)
  full_dict = get_dictionary()
  words, corrected_words, triggered = text.split(), [], False

  for word in words:
    if word.isalpha() and word not in full_dict:
      best_match, lowest_dist = None, 2 
      for dict_word in full_dict:
        if abs(len(word) - len(dict_word)) > lowest_dist: continue
        dist = get_levenshtein(word, dict_word)
        if dist < lowest_dist:
          lowest_dist, best_match = dist, dict_word
        if lowest_dist == 1: break

      if best_match:
        corrected_words.append(best_match)
        triggered = True
        continue
    corrected_words.append(word)

  if triggered:
    suggested = " ".join(corrected_words)
    app_tables.session.add_row(id=conversation_id, key="pending_correction", value=str({'original': text, 'suggested': suggested}))
    return {"response": f"Did you mean: '{suggested}'?", "id": conversation_id}

  return {"response": run_logic(text), "id": conversation_id}

@callable
def run_action(fn, args={}):
  """Executes multi-line Python code. Captures 'result' variable."""
  row = app_tables.database.get(Names=fn)
  if row:
    namespace = {}
    code = str(row['Object'])
    for k, v in args.items():
      code = code.replace(f"<{k}>", str(v))
    try:
      exec(code, {"__builtins__": __builtins__}, namespace)
      return namespace.get("result", f"Action {fn} finished.")
    except Exception as e:
      return f"Code error in {fn}: {str(e)}"
  return f"Action '{fn}' not found."

def run_logic(text):
  """Core Brain: Facts and Actions."""
  db = app_tables.database

  # Dynamic Fact Check
  if text.startswith("what is"):
    subject = text.replace("what is", "").replace("the", "").replace("of", "").strip()
    row = db.get(Names=subject)
    if row:
      stored_val = str(row['Object'])
      if db.get(Names=stored_val) and "<" not in stored_val:
        return run_action(stored_val)
      return f"{subject} is {stored_val}"

    # Do Action
  if text.startswith("do "):
    fn_name = text[3:].strip()
    return run_action(fn_name, {})

  for i in [" is "," are "]:
    if " is " in text:
      parts = text.split(" is ", 1)
      if parts[0].endswith('that') or parts[0].endswith('which'):
        return "sorry, i can't do that yet"
      db.add_row(Names=parts[0].strip(), Object=parts[1].strip())
      return f"Confirmed: {parts[0].strip()} is {parts[1].strip()}"

  return "I heard you, but I have no rule for that command yet."

@callable
def learn_from_webpage(url):
  """Scrapes URL and feeds sentences into run_logic."""
  try:
    res = requests.get(url, timeout=10)
    soup = BeautifulSoup(res.text, 'html.parser')
    for s in soup(["script", "style", "nav", "footer"]): s.decompose()
    sentences = re.split(r'[.!?\n]', soup.get_text(separator=' '))
    count = 0
    for sent in sentences:
      clean = sent.strip().lower()
      if 5 <= len(clean.split()) <= 15:
        run_logic(clean)
        count += 1
    return f"Bulk learned {count} items from {url}."
  except Exception as e:
    return f"Scrape error: {str(e)}"
