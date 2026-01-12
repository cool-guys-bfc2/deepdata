import anvil.server
import requests
import io
import random
from PIL import Image
from PIL.ExifTags import TAGS

GITHUB_USER = "cool-guys-bfc2"
GITHUB_REPO = "images"

@anvil.server.callable
def detect_subject_and_blend(prompt):
  # 1. Fetch file list from GitHub
  api_url = f"https://api.github.com/{GITHUB_USER}/{GITHUB_REPO}/git/trees/main?recursive=1"
  files = requests.get(api_url).json().get('tree', [])

  potential_matches = []

  # 2. "Check" the subject of random photos
  # We filter by folder name or by scanning internal metadata
  random.shuffle(files)
  for f in files:
    if f['path'].endswith(('.jpg', '.jpeg')) and len(potential_matches) < 2:
      # Check if folder name matches prompt (Subject Detection)
      if prompt.lower() in f['path'].lower():
        potential_matches.append(f['path'])
        continue

        # OR: Download and check EXIF metadata for 'Keywords' or 'Subject'
      raw_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{f['path']}"
      img_data = requests.get(raw_url).content
      img = Image.open(io.BytesIO(img_data))

      exif = img.getexif()
      if exif:
        # Check all tags for a match to the prompt
        for tag_id, value in exif.items():
          tag = TAGS.get(tag_id, tag_id)
          if prompt.lower() in str(value).lower():
            potential_matches.append(f['path'])
            break

  if len(potential_matches) < 2:
    return None

    # 3. Download and Blend
  images = []
  for path in potential_matches:
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/{path}"
    data = requests.get(raw_url).content
    images.append(Image.open(io.BytesIO(data)).convert("RGBA"))

    # Align and Blend
  base = images[0]
  overlay = images[1].resize(base.size)
  blended = Image.blend(base, overlay, alpha=0.5)

  # 4. Return to Anvil
  out = io.BytesIO()
  blended.save(out, format='PNG')
  return anvil.BlobMedia('image/png', out.getvalue(), name="blended.png")
