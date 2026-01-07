import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import requests

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
#

operation_words=[
  "a","and","an","is","or","not"
]

@anvil.server.callable
def english():
  return requests.get('https://raw.githubusercontent.com/dwyl/english-words/refs/heads/master/words.txt').text.split("\n")

@anvil.server.callable
def replace(x,k,v):
  return v.join(x.split(k))

@anvil.server.callable
def hasdata(t,name):
  return len(t.search(Names=name))>0

@anvil.server.callable
def getrow(t,name):
  return t.search(Names=name)[len(t.search(Names=name))-1]

@anvil.server.callable
def clean(t,l):
  global operation_words
  x=0
  for i in l:
    if i in operation_words:
      continue
    c=False
    j=x
    for z in range(len(l)-x):
      thing=" ".join(l[x:j+1])
      c=(c or hasdata(t,thing))
      if hasdata(t,thing):
        l[l.index(thing)]=getrow(t,thing)['Object']
    if not c:
      for k in range(x,j):
        del l[k]
      j+=1
    x+=1
  return l

data='n'
func='n'
@anvil.server.callable
def run(text):
  global data,func
  data=app_tables.database
  func=app_tables.actions
  w=text.split(' ')
  mode="none"
  d1=[]
  d2=[]
  for i in w:
    ignore=['a','an']
    modeset=["is","are"]
    if i in modeset:
      mode="set"
      continue
    if mode=="none":
      for j in modeset:
        if j in w:
          if i not in ignore:
            d1.append(i)
            break
    if mode=="set":
      d2.append(i)
  if mode=="set":
    d2=clean(app_tables.database,d2)[:]
    s1=" ".join(d1)
    s2=" ".join(d2)
    if not hasdata(app_tables.database,s1):
      app_tables.database.add_row(ID=str(len(app_tables.database.search())),Names=s1,Object=str(s2))
    else:
      getrow(app_tables.database,s1)['Object']+="\n"+str(s2)
  return "MODE: "+mode+"!"