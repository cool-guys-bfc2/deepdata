import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import requests

# Words to ignore during the internal definition linkage process
operation_words = ["a", "and", "an", "is", "are", "or", "not", "the"]

@anvil.server.callable
def replace(x, k, v=""):
  """Utility to replace substrings safely."""
  return v.join(str(x).split(str(k)))

@anvil.server.callable
def hasdata(t, name):
  """Check if a name exists in the database table."""
  return len(t.search(Names=name)) > 0

@anvil.server.callable
def getrow(t, name):
  """
    Safely retrieves a row. 
    Returns a fallback dict if not found to prevent 'string indices' errors.
    """
  results = t.search(Names=name)
  if len(results) > 0:
    # Return the actual row object
    return results[0]
    # Fallback dictionary prevents crash if row is missing
  return {"Object": "Unknown", "Names": name}

@anvil.server.callable
def clean(t, l):
  """Replaces words in a list with their database definitions if they exist."""
  global operation_words
  new_list = l[:]
  for i, word in enumerate(new_list):
    if word.lower() in operation_words:
      continue
    if hasdata(t, word):
      row = getrow(t, word)
      new_list[i] = str(row['Object'])
  return new_list

@anvil.server.callable
def filter_text(x):
  """Removes numbers and filler words from the subject string for cleaner searching."""
  y = x.lower()
  ignore = ["an", "a", "the", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
  words = y.split()
  result = [w for w in words if w not in ignore]
  return " ".join(result)

@anvil.server.callable
def run(rtext):
  """
    Core AI Logic. 
    'Set' mode: [Subject] is [Fact]
    'Val' mode: What is [Subject]
    """
  text = rtext.strip()
  if not text:
    return ""

  data = app_tables.database
  w = text.split(' ')

  # Clean possessives (e.g. "Sky's" -> "Sky")
  w = [word[:-2] if word.lower().endswith("'s") else word for word in w]

  modeset = ["is", "are"]
  modeval = ["what", "who", "where"]

  # Determine Mode
  mode = "none"
  word_list_lower = [word.lower() for word in w]

  if any(m in word_list_lower for m in modeval):
    mode = "val"
  elif any(m in word_list_lower for m in modeset):
    mode = "set"

    # Separate Subject (d1) and Object (d2)
  d1, d2 = [], []
  found_verb = False
  for i in w:
    if i.lower() in modeset:
      found_verb = True
      continue
    if not found_verb:
      # Building the subject
      if i.lower() not in modeval and i.lower() not in ["a", "an", "the"]:
        d1.append(i)
    else:
      # Building the description
      d2.append(i)

    # ACTION: LEARN (Set Mode)
  if mode == "set" and d1 and d2:
    s1 = " ".join(d1).strip()
    # Resolve any internal references in the description (AI "thinks" about what it already knows)
    d2_resolved = clean(data, d2)
    s2 = " ".join(d2_resolved).strip()

    if not hasdata(data, s1):
      data.add_row(ID=str(len(data.search())), Names=s1, Object=s2)
    else:
      row = getrow(data, s1)
      # Update existing knowledge if it's a real Row object (not the fallback dict)
      if not isinstance(row, dict):
        row['Object'] += " and " + s2
    return f"Confirmed: {s1} is {s2}"

    # ACTION: ANSWER (Val Mode)
  if mode == "val":
    subject = filter_text(" ".join(d2))
    row = getrow(data, subject)
    if row["Object"] == "Unknown":
      return f"I do not know what '{subject}' is yet."
    return f"{subject} is {row['Object']}"

  return "Mode detected: " + mode

@anvil.server.callable
def learnfromurl(url):
  """
    Fetches text from a URL and teaches the AI line by line.
    Prints progress to the Anvil Console for real-time monitoring.
    """
  try:
    print(f"--- STARTING KNOWLEDGE ACQUISITION: {url} ---")
    response = requests.get(url, timeout=15)
    content = response.text

    # Split into sentences based on common punctuation
    lines = content.replace(".", "\n").replace("?", "\n").replace("!", "\n").split("\n")

    learned_count = 0
    for line in lines:
      clean_line = line.strip()

      # 2026 Complexity Filter: Skip sentences with logic your AI can't handle yet
      bad_triggers = [" if ", " whether ", " but ", " however ", " although ", " maybe "]
      if any(trigger in clean_line.lower() for trigger in bad_triggers):
        continue

        # Length filter: Ignore headers, single words, or massive paragraphs
      word_count = len(clean_line.split())
      if 3 <= word_count <= 15:
        # Check for "is" or "are" to ensure it's a declarative fact
        if any(verb in f" {clean_line.lower()} " for verb in [" is ", " are "]):
          result = run(clean_line)
          print(f"LEARNED: {clean_line}")
          learned_count += 1

    print(f"--- SUCCESS: Learned {learned_count} new facts from source. ---")

  except Exception as e:
    print(f"--- ERROR: Could not process URL. {str(e)} ---")
