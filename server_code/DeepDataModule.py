import anvil.server
import requests
import io
from bs4 import BeautifulSoup
from PIL import Image, ImageEnhance

@anvil.server.callable
def generate_on_cpu(prompt):
  # 1. Search Google Images via direct URL
  search_url = f"https://www.google.com/search/?q={prompt.replace(' ', '+')}&tbm=isch"
  headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) App-2026"}

  try:
    response = requests.get(search_url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 2. Extract image tags (Google uses specific <img> classes for thumbnails)
    img_tags = soup.find_all("img")
    # Filter for actual image data (skipping the Google logo/icons)
    urls = [img.get("src") for img in img_tags if img.get("src") and img.get("src").startswith("http")]

    if len(urls) < 2:
      return "Error: Could not find enough visual data for this prompt."

      # 3. Fetch and Blend (CPU Synthesis)
    img1_data = requests.get(urls[1]).content # Index 1 is usually the first result
    img2_data = requests.get(urls[2]).content

    img1 = Image.open(io.BytesIO(img1_data)).convert("RGBA").resize((800, 600))
    img2 = Image.open(io.BytesIO(img2_data)).convert("RGBA").resize((800, 600))

    # Synthesize a unique result
    final_img = Image.blend(img1, img2, alpha=0.5)

    # 4. Final Polish
    enhancer = ImageEnhance.Contrast(final_img)
    final_img = enhancer.enhance(1.3)

    bs = io.BytesIO()
    final_img.save(bs, format="PNG")
    return anvil.BlobMedia("image/png", bs.getvalue(), name="gen.png")

  except Exception as e:
    return f"Error: {str(e)}"
