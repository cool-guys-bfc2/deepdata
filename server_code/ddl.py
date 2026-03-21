import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.secrets
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import math
import anvil.media
import io
from PIL import Image
import numpy as np
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
  m,m2=0,0
  for ia1 in a:
    for ia in ia1:
      if True:
        if True:
          ib=b[m2][m]
          if isinstance(ia,list):
            oa=ia
            ob=ib
            ia=0
            ib=0
            ind=0
            for i in oa:
              ia+=i*(256**ind)
              ind+=1
            ind=0
            for i in ob:
              ib+=i*(256**ind)
              ind+=1
          r.append(isclose(ia,ib))
      m+=1
    m2+=1
  return avgb(r)


@anvil.server.callable
def image_to_3d_list(media_object):
  # 1. Load the Anvil Media Object into Pillow
  img_bytes = media_object.get_bytes()
  img = Image.open(io.BytesIO(img_bytes))

  # 2. Convert to RGB (ensures 3 color channels: 0-255)
  img = img.convert('RGB')

  # 3. Convert to a 3D list: [rows [columns [R, G, B]]]
  # Shape: (height, width, 3)
  pixel_3d_list = np.array(img).tolist()

  return pixel_3d_list

@anvil.server.callable
def images(m1,m2):
  l1=image_to_3d_list(m1)
  l2=image_to_3d_list(m2)
  return img(l1,l2)

def vectorized_is_close(arr1, arr2, scale=1):
  # This replaces your Boolean class and isclose function logic
  # d = abs(x-y)/10**(scale-1)
  diff = np.abs(arr1 - arr2) / (10**(scale - 1))

  # Implementing your 'issmall' logic via your sr (sqrt) formulas
  # Note: If you just want a standard "closeness" threshold, 
  # you can just do: return diff < 1.0
  x = diff + 2
  srx = np.sqrt(x)
  y = x - srx
  z = np.sqrt(y)
  r = 1 - (np.sqrt(z) / z) # Note: Fixed the 'sr/z' typo in your original logic

  # Return fuzzy values (0 to 1)
  return 1 - np.clip(r, 0, 1)

@anvil.server.callable
def images_fast(m1, m2,mode='bool'):
  # 1. Load images into NumPy arrays immediately
  img1 = Image.open(io.BytesIO(m1.get_bytes())).convert('RGB')
  img2 = Image.open(io.BytesIO(m2.get_bytes())).convert('RGB')
  img1=img1.resize((200,200))
  img2=img2.resize((200,200))
  # Ensure they are the same size
  if img1.size != img2.size:
    return 0# Or handle resizing

  a1 = np.array(img1, dtype=np.float64)
  a2 = np.array(img2, dtype=np.float64)

  # 2. Convert RGB to single values (like your 256**ind logic)
  # Using dot product for [R, G, B] -> R + G*256 + B*65536
  weights = np.array([1, 256, 65536])
  v1 = np.dot(a1, weights)
  v2 = np.dot(a2, weights)

  # 3. Apply your fuzzy logic across the whole array
  closeness_map = vectorized_is_close(v1, v2)

  # 4. Return the average (like your avgb)
  x=Boolean(float(np.mean(closeness_map)))
  if True:
    if mode=='bool':
      return x.tobool()
    if mode=='num':
      return x.v
