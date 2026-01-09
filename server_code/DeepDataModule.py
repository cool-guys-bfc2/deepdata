import anvil.secrets
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from anvil.server import callable
import requests, re, random
from bs4 import BeautifulSoup

# --- EXTENSIBILITY: External Logic Environment ---
# Define or import functions from other files here
def external_tool_example(data):
  print(f"External Tool Logic Triggered with: {data}")

# This dictionary is passed to eval() and exec()
GLOBAL_ENV = {
  "requests": requests,
  "re": re,
  "random": random,
  "app_tables": app_tables,
  "ext_tool": external_tool_example 
}

# --- CONFIGURATION & DICTIONARY ---
DICTIONARY_URL = anvil.secrets.get_secret('englishdict')
cached_dict = set()

def get_dictionary():
  global cached_dict
  if not cached_dict:
    try:
      res = requests.get(DICTIONARY_URL, timeout=15)
      if res.status_code == 200:
        cached_dict = {w.strip().lower() for w in res.text.splitlines() if w.strip()}
    except: pass
  return cached_dict

# --- NLP UTILITIES (Singularization & Synonyms) ---
def to_singular(word):
  """Basic 2026 rule-based singularization."""
  if not word: return ""
  word = word.lower()
  if word.endswith("ies"): return word[:-3] + "y"
  if word.endswith("es"): return word[:-2]
  if word.endswith("s") and not word.endswith("ss"): return word[:-1]
  return word

def apply_database_synonyms(text):
  words = text.split()
  db_rows = app_tables.database.search()
  synonym_map = {}
  for row in db_rows:
    if row['Synonyms']:
      for s in row['Synonyms'].split(','):
        synonym_map[s.strip().lower()] = row['Names'].lower()
  return " ".join([synonym_map.get(word, word) for word in words])

# --- MAIN ENTRY POINT ---
@callable
def run(rtext, conversation_id=None):
  if conversation_id is None:
    conversation_id = int(random.randint(100, 999))

  text = apply_database_synonyms(rtext.strip().lower())
  if not text: return {"response": "", "id": conversation_id}

    # Session State (Confirmation Logic)
  state = app_tables.session.get(id=int(conversation_id), key="pending_correction")
  if state and state['value']:
    pending_data = eval(state['value'])
    if text in ["yes", "y", "yeah", "correct"]:
      state.delete()
      return run(pending_data['suggested'], conversation_id)
    elif text in ["no", "n", "nope"]:
      state.delete()
      return run(pending_data['original'], conversation_id)

    # Autocorrect check (Omitted here for brevity, logic as previously established)

  return {"response": run_logic(text), "id": conversation_id}

# --- LOGIC BRAIN ---
def run_logic(text):
  db = app_tables.database

  # 1. DYNAMIC ACTION EXECUTION (ignores 'with' and 'and')
  if text.startswith("do "):
    # Regex to strip 'with' and 'and' as standalone words
    clean_command = re.sub(r'\b(with|and)\b', '', text[3:])
    parts = clean_command.split()
    if not parts: return "Do what?"

    action_name = parts[0]
    args = parts[1:] # Remaining parts are data arguments
    return run_action(action_name, args)

    # 2. VERB-BASED LEARNING (Singularizes Subjects/Objects)
    # Pattern: [Subject] [Verb] [Description]
  match = re.search(r"(\w+)\s+(is|are|has|contains|owns)\s+(.+)", text)
  if match and not text.startswith('what is'):
    subject = to_singular(match.group(1))
    verb = match.group(2)
    # Normalize 'are' to 'is' for database consistency
    canonical_verb = "is" if verb == "are" else verb
    obj = to_singular(match.group(3)) if canonical_verb == "is" else match.group(3)

    val_to_store = f"{canonical_verb} {obj}"
    existing = db.get(Names=subject)
    if existing: existing['Object'] = val_to_store
    else: db.add_row(Names=subject, Object=val_to_store)
    return f"Confirmed: {subject} {val_to_store}"

    # 3. KNOWLEDGE RETRIEVAL
  if text.startswith("what is"):
    subject = to_singular(text.replace("what is", "").replace("the", "").strip())
    row = db.get(Names=subject)
    if row:
      stored = str(row['Object'])
      if stored.startswith("py:"):
        try:
          res = eval(stored[3:], {"__builtins__": None}, GLOBAL_ENV)
          return f"Result: {res}"
        except Exception as e: return f"Eval Error: {e}"
      return f"{subject} {stored}"
    return f"I don't have information on {subject}."

  return "I recognized the words but don't have a logic pattern for that yet."

# --- EXECUTION ENGINE ---
def run_action(action_name, args):
  """Executes multi-line code with filtered arguments."""
  row = app_tables.database.get(Names=action_name)
  if row:
    code = str(row['Object'])
    # Context includes arguments and external tools
    exec_context = GLOBAL_ENV.copy()
    exec_context['args'] = args 

    try:
      exec(code, {"__builtins__": __builtins__}, exec_context)
      return f"Action '{action_name}' completed with {len(args)} args."
    except Exception as e:
      return f"Action Error ({action_name}): {str(e)}"
  return f"Action '{action_name}' not found."

# --- WIKIPEDIA LEARNING ---
@callable
def learn_from_wikipedia(url, conversation_id=None):
  if conversation_id is None: conversation_id = 0
  try:
    headers = {'User-Agent': 'Anvil-AI-Core-2026'}
    res = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(res.text, 'html.parser')

    content = soup.find(id="mw-content-text")
    if not content: return "Invalid Wikipedia structure."

    paragraphs = content.find_all('p')
    count = 0
    for p in paragraphs[:10]: # Process top 10 paragraphs
      text = p.get_text().strip()
      # Clean citations [1], [2], etc.
      clean_text = re.sub(r'\[\d+\]|\[citation needed\]', '', text)
      sentences = re.split(r'[.!?]\s', clean_text)

      for sent in sentences:
        if " is " in sent.lower() or " are " in sent.lower():
          # Funnel through run() for singularization and mapping
          run(sent, conversation_id)
          count += 1
    return f"Learned {count} items from {url}."
  except Exception as e:
    return f"Wikipedia Error: {str(e)}"

@callable
def learn_from_url(url, conversation_id=None):
  if conversation_id is None: conversation_id = 0
  try:
    headers = {'User-Agent': 'Anvil-AI-Core-2026'}
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()

    # Create soup and remove only strictly non-readable metadata
    soup = BeautifulSoup(res.text, 'html.parser')
    for script_or_style in soup(["script", "style", "meta", "noscript"]):
      script_or_style.decompose()

    # Get all text from the document at once
    # separator=" " ensures words from adjacent tags don't merge
    raw_text = soup.get_text(separator=" ", strip=True)

    # Split by common sentence terminators
    sentences = re.split(r'[.!?]\s', raw_text)
    count = 0

    for sent in sentences:
      clean_sent = sent.strip()
      # Only process sentences likely to contain useful facts
      if 20 < len(clean_sent) < 300:
        if " is " in clean_sent.lower() or " are " in clean_sent.lower():
          run(clean_sent, conversation_id)
          count += 1

    return f"Learned {count} items from the entire page at {url}."
  except Exception as e:
    return f"Universal Learning Error: {str(e)}"
