import anvil.secrets
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import re

# This is a server module. It runs on the Anvil server,
# rather than in the user's browser.
#
# To allow anvil.server.call() to call functions here, we mark
# them with @anvil.server.callable.
# Here is an example - you can replace it with your own:
#
# @anvil.server.callable
# def say_hello(name):
#   print("Hello, " + name + "!")
#   return 42
#for word arguments use (\w+) in key and \(number of argument) in value
#for things that can be a or b you use (a|b)

lang={
  '# (is|are) #':r'\1 us \2',
  'not #':r'nu \1',
  '(a|an|one|single) #':r'um \1',
  'no':'nu'
}
langw={
  'apple':'$apal',
  'bannana':'ban$ana'
}
def format(x):
  return x.replace('$a','\u0101')
"""
@anvil.server.callable
def translate(x):
  for k in lang:
    v=lang[k]
    x=re.sub(re.escape(k.replace('#','(\\w+)')),v,x)
  for k in langw:
    v=langw[k]
    x=x.replace(' '+k+' ',' '+v+' ')
  return format(x)
"""
@anvil.server.callable
def translate(x):
  # Process phrases with placeholders
  lw=langw
  x=x.lower().strip()
  y=x.split(' ')
  ind=0
  for i in y:
    if i[len(i)-1] in [',','.',"!",'?']:
      i=list(i)
      i=i[:-1]
      i=''.join(i)
    if i[len(i)-1]=='s' and i[len(i)-2] in ["'","e"]:
      ix=list(i)
      ix[len(i)-2:]='es'
      y[ind]=''.join(ix)
    ind+=1
  x=format(' '.join(y))

  x=x.lower()
  for k, v in lang.items():
    # Create the pattern: turn '#' into '(\w+)'
    # We don't use re.escape here because we want the () to be active
    for i in k.split(' '):
      if i
    pattern = k.replace('#', r'(\w+)')
    x = re.sub(pattern, v, x, flags=re.IGNORECASE)

    # Process individual word replacements
  for k, v in lw.items():
    # warning: Using \b (word boundaries) is safer than ' '+k+' '
    x = x.replace(k,v)
  y=x.split(' ')
  ind=0
  for i in y:
    if i[len(i)-1] in [',','.',"!",'?']:
      i=''.join(list(i)[:-1])
    ind+=1
  return format(' '.join(y))
