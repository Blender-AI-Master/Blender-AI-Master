"""把 Blender-AI Master logo 放大到 2x + 透明度优化"""
import os
from PIL import Image

src = r"C:\Users\Administrator\Desktop\jietu\12.png"
dst = r"I:\Projects-2026\CLI-Anything-Blender\resources\branding\blender-ai-wordmark-white.png"

img = Image.open(src).convert("RGBA")
w, h = img.size
print(f"原图: {img.size}")

# 放大 2 倍
img = img.resize((w * 2, h * 2), Image.LANCZOS)
print(f"放大后: {img.size}")

# 处理颜色: 白底 → 透明, 深色 → 纯白
pixels = img.load()
nw, nh = img.size
for y in range(nh):
    for x in range(nw):
        r, g, b, a = pixels[x, y]
        brightness = (r + g + b) / 3
        if brightness > 240:
            pixels[x, y] = (255, 255, 255, 0)
        else:
            pixels[x, y] = (255, 255, 255, 255)

img.save(dst, "PNG")
print(f"saved: {dst}")

import os
print(f"size: {os.path.getsize(dst)} bytes")
