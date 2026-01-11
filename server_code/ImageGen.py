import anvil.server
import torch
import torchvision.transforms as transforms
import io

@anvil.server.callable
def generate_on_cpu():
  # 1. Create a 3-channel (RGB) tensor with random noise
  # Shape: [Channels, Height, Width]
  #shape = (3, 512, 512)

  # Example: Generating a gradient or pattern using pure torch math
  # Here we create a simple RGB gradient
  x = torch.linspace(0, 1, 512)
  y = torch.linspace(0, 1, 512)
  grid_x, grid_y = torch.meshgrid(x, y, indexing='ij')

  # Stack to create RGB channels
  # Red increases horizontally, Green increases vertically, Blue is static
  image_tensor = torch.stack([grid_x, grid_y, torch.full_like(grid_x, 0.5)])

  # 2. Convert Tensor to PIL Image using torchvision
  # Ensure values are in [0, 1] range for float32
  transform = transforms.ToPILImage()
  pil_image = transform(image_tensor)

  # 3. Save to memory for Anvil
  img_byte_arr = io.BytesIO()
  pil_image.save(img_byte_arr, format='PNG')

  return anvil.BlobMedia("image/png", img_byte_arr.getvalue(), name="torch_pattern.png")
