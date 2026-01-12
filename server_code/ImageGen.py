import anvil.server
import requests
import io
import random
from PIL import Image, ImageStat, ImageDraw

USER = "cool-guys-bfc2"
REPO = "images"

@anvil.server.callable
def generate_synthetic_image(prompt):
  # 1. Fetch matching images from GitHub
  api_url = f"https://api.github.com/{USER}/{REPO}/git/trees/main?recursive=1"
  files = requests.get(api_url).json().get('tree', [])
  subject_files = [f['path'] for f in files if prompt.lower() in f['path'].lower()]

  if not subject_files:
    return None

    # 2. Sample 64 quadrants from a random matching image
  target_path = random.choice(subject_files)
  raw_url = f"https://raw.githubusercontent.com/{USER}/{REPO}/main/{target_path}"
  img = Image.open(io.BytesIO(requests.get(raw_url).content)).convert("RGB")

  # 3. Create a New Canvas for Generation
  gen_img = Image.new('RGB', (512, 512), color=(255, 255, 255))
  draw = ImageDraw.Draw(gen_img)

  # Grid math
  w, h = img.size
  qw, qh = w // 8, h // 8  # Source quadrants
  dw, dh = 512 // 8, 512 // 8  # Destination quadrants

  # 4. Generate by Copying Average Color & Shape Density
  for i in range(8):
    for j in range(8):
      # Sample Area
      box = (j*qw, i*qh, (j+1)*qw, (i+1)*qh)
      quad = img.crop(box)

      # Get Average Color
      avg_color = tuple([int(x) for x in ImageStat.Stat(quad).mean])

      # Calculate 'Shape Complexity' (Standard Deviation of pixels)
      complexity = sum(ImageStat.Stat(quad).stddev)

      # Draw the base quadrant color
      dst_box = [j*dw, i*dh, (j+1)*dw, (i+1)*dh]
      draw.rectangle(dst_box, fill=avg_color)

      # "Generate" shape detail based on complexity
      # If the area is complex, we add 'noise' shapes to simulate detail
      if complexity > 30:
        for _ in range(int(complexity // 10)):
          rx = random.randint(dst_box[0], dst_box[2])
          ry = random.randint(dst_box[1], dst_box[3])
          draw.point((rx, ry), fill=(255, 255, 255))

    # 5. Return the generated image to Anvil
  out = io.BytesIO()
  gen_img.save(out, format='PNG')
  return anvil.BlobMedia('image/png', out.getvalue(), name="generated.png")
