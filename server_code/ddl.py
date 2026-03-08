import anvil.secrets
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import math
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

class Boolean(object):
  def __init__(self,obj=1):
    if isinstance(obj,bool):
      if obj:
        self.v=1
      else:
        self.v=0
    else:
      self.v=obj
  def cand(self,o):
    return Boolean(self.v*o.v)
  def cor(self,o):
    return Boolean(min([1,self.v+o.v]))
  def cnot(self):
    return Boolean(1-self.v)
  def tobool(self):
    x=round(self.v)
    if x==1:
      return True
    elif x==0:
      return False
    else:
      return None
      
def sr(x):
  y=math.sqrt(x)
  z=round(1000000*y)/1000000
  return z
def isbig(x):
  x=abs(x)+2
  srx=sr(x)
  y=x-srx
  z=sr(y)
  r=1-(sr/z)
  fr=Boolean(r)
  return fr
def issmall(x):
  return isbig(x).cnot()
def isclose(x,y,scale=1):
  d=abs(x-y)/10**(scale-1)
  c=issmall(d)
  return c

def repor(x):
  r=Boolean(False)
  for i in x:
    r=r.cor(i)
  return r
def repand(x):
  r=Boolean(True)
  for i in x:
    r=r.cand(i)
  return r
def avg(x):
  r=0
  for i in x:
    r+=i/len(x)
  return r
def avgb(x):
  return Boolean(avg([i.v for i in x]))
def img(a,b):
  r=[]
  for ia1 in a:
    for ia in ia1:
      for ib1 in b:
        for ib in ib1:
          if isinstance(ia,list)
          r.append(isclose(ia,ib))