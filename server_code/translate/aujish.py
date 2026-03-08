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

lang={
  '# is #':r'\1 us \2',
  'not #':r'nu \1',
  'a #':r'um \1',
  'an #':r'um \1'
}
langw={
  'apple':'$apal',
  'bannana':'ban$ana',
  'no':'nu'
}
def format(x):
  return x.replace('$a','\u0101')
  
@anvil.server.callable
def translate(x):
  for k in lang:
    v=lang[k]
    x=re.sub(re.escape(k.replace('#','(\\w+)')),v,x)
  for k in langw:
    v=langw[k]
    x=x.replace(' '+k+' ',' '+v+' ')
  return format(x)
  