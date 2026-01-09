import anvil.secrets
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from anvil.server import callable
import requests
import re
import random
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
DICTIONARY_URL=anvil.secrets.get_secret('englishdict')
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
  """Calculates the edit distance rating (Lower = Closer)."""
  if len(s1) < len(s2): return get_levenshtein(s2, s1)
  if len(s2) == 0: return len(s1)
  prev = range(len(s2) + 1)
  for i, c1 in enumerate(s1):
    curr = [i + 1]
    for j, c2 in enumerate(s2):
      ins, dele, subs = prev[j+1]+1, curr[j]+1, prev[j]+(c1!=c2)
      curr.append(min(ins, dele, subs))
    prev = curr
  return prev[-1]

def generate_unique_3digit_id():
  """Generates unique ID (100-999). Clears 10 oldest rows if full."""
  used_ids = {r['id'] for r in app_tables.session.search()}
  all_possible = set(range(100, 1000))
  available = list(all_possible - used_ids)

  if not available:
    for row in list(app_tables.session.search())[:10]: row.delete()
    used_ids = {r['id'] for r in app_tables.session.search()}
    available = list(all_possible - used_ids)

  return random.choice(available)

@callable
def run(rtext, conversation_id=None):
  """Entry Point. Manages Session State, Autocorrect, and Logic."""
  if conversation_id is None:
    conversation_id = generate_unique_3digit_id()

  text = rtext.strip().lower()
  if not text: return {"response": "", "id": conversation_id}

    # 1. SESSION STATE: Check for correction confirmation
  state = app_tables.session.get(id=conversation_id, key="pending_correction")
  if state and state['value']:
    pending_data = eval(state['value'])
    if text in ["yes", "y", "yeah", "correct"]:
      actual_text = pending_data['suggested']
      state.delete()
      return {"response": run_logic(actual_text), "id": conversation_id}
    elif text in ["no", "n", "nope"]:
      actual_text = pending_data['original']
      state.delete()
      return {"response": run_logic(actual_text), "id": conversation_id}
    else:
      return {"response": f"Waiting for yes/no. Did you mean: '{pending_data['suggested']}'?", "id": conversation_id}

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

def run_logic(text):
  """The Brain: Dynamic Retrieval, Facts, and Actions."""
  db = app_tables.database

  # A. DYNAMIC RETRIEVAL (what is ...)
  if text.startswith("what is"):
    subject = text.replace("what is", "").replace("the", "").replace("of", "").strip()
    row = db.get(Names=subject)
    if row:
      stored_val = str(row['Object']).strip()

      # 1. Dynamic Python Expressions
      if stored_val.startswith("py:"):
        try:
          expr = stored_val[3:].strip()
          result = eval(expr, {"__builtins__": __builtins__}, {})
          return f"The {subject} is {result}"
        except Exception as e:
          return f"Error evaluating {subject}: {str(e)}"

          # 2. Pointer to Multi-line Action
      action_exists = db.get(Names=stored_val)
      if action_exists and "<" not in stored_val:
        return run_action(stored_val)

      return f"{subject} is {stored_val}"
    return f"I don't know what {subject} is yet."

    # B. COMPLEX QUERIES (is ..., which ..., what attribute ...)
  if text.startswith("is "):
    parts = re.sub(r"^(is the|is a|is) ", "", text).split(" ", 1)
    if len(parts) == 2:
      row = db.get(Names=parts[0].strip())
      if row:
        stored = str(row['Object']).lower()
        return "Yes" if parts[1].strip() in stored else f"No, it is {stored}"

    # C. DO ACTIONS
  if text.startswith("do "):
    fn_name = text[3:].strip()
    return run_action(fn_name, {})

    # D. FACT LEARNING
  if " is " in text:
    parts = text.split(" is ", 1)
    name, obj = parts[0].strip(), parts[1].strip()
    if any(x in name for x in ["that", "which", "who"]):
      return "Sorry, I can't process complex clauses yet."

    existing = db.get(Names=name)
    if existing: existing['Object'] = obj
    else: db.add_row(Names=name, Object=obj)
    return f"Learned: {name} is now {obj}"

  return "I understood the words, but have no logic for that command."

@callable
def run_action(fn, args={}):
  """Executes multi-line Python code. Result must be in 'result' variable."""
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
      return f"Code error: {str(e)}"
  return f"Action '{fn}' not found."

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
      if 5 <= len(clean.split()) <= 20:
        run_logic(clean)
        count += 1
    return f"Bulk learned {count} items from {url}."
  except Exception as e:
    return f"Scrape error: {str(e)}"
