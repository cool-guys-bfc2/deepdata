import anvil.server
import requests
import io
import time
from PIL import Image, ImageEnhance
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

@anvil.server.callable
def generate_on_cpu(prompt):
  """
    Simulates a Google Image search to retrieve visual data 
    and synthesizes a unique result on the CPU.
    """
  # 1. SETUP HEADLESS BROWSER (2026 Stealth Mode)
  chrome_options = Options()
  chrome_options.add_argument("--headless")
  chrome_options.add_argument("--no-sandbox")
  chrome_options.add_argument("--disable-dev-shm-usage")
  chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) 2026-App")

  driver = webdriver.Chrome(options=chrome_options)

  try:
    # 2. SEARCH GOOGLE IMAGES
    search_query = prompt.replace(" ", "+")
    url = f"https://www.google.com/search?q={search_query}&tbm=isch"
    driver.get(url)

    # Wait for dynamic content to load
    time.sleep(2) 

    # 3. EXTRACT IMAGE ELEMENTS
    # Locate image tags nested inside Google's dynamic container
    img_elements = driver.find_elements(By.CSS_SELECTOR, "img.Q4LuWd")

    image_urls = []
    for img in img_elements[:5]: # Get first 5 to ensure quality
      src = img.get_attribute("src")
      if src and src.startswith("http"):
        image_urls.append(src)

    if len(image_urls) < 2:
      return "Error: Google did not return enough image data for this prompt."

      # 4. DOWNLOAD & PROCESS DATA
      # Fetch two different images for synthesis
    resp1 = requests.get(image_urls[0], timeout=10)
    resp2 = requests.get(image_urls[1], timeout=10)

    img1 = Image.open(io.BytesIO(resp1.content)).convert("RGBA").resize((1024, 768))
    img2 = Image.open(io.BytesIO(resp2.content)).convert("RGBA").resize((1024, 768))

    # 5. CPU SYNTHESIS
    # Create a unique composition by blending the results
    generated_img = Image.blend(img1, img2, alpha=0.5)

    # Apply professional 2026 contrast boost
    enhancer = ImageEnhance.Contrast(generated_img)
    generated_img = enhancer.enhance(1.3)

    # 6. RETURN AS ANVIL MEDIA
    bs = io.BytesIO()
    generated_img.save(bs, format="PNG")
    return anvil.BlobMedia("image/png", bs.getvalue(), name="google_gen.png")

  except Exception as e:
    return f"Generation Error: {str(e)}"
  finally:
    driver.quit() # Always close the browser
