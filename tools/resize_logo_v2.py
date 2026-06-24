"""最终方案: 把 Blender-AI Master logo 处理成 Blender previews 友好的大尺寸 PNG"""
import os
from PIL import Image

src = r"C:\Users\Administrator\Desktop\jietu\12.png"
dst = r"I:\Projects-2026\CLI-Anything-Blender\resources\branding\blender-ai-wordmark-white.png"

img = Image.open(src).convert("RGBA")
w, h = img.size
print(f"原图: {w}x{h}")

# 放大到 4 倍(确保 previews 缩到 32x 时仍然清晰)
scale = 4
new_size = (w * scale, h * scale)
img = img.resize(new_size, Image.LANCZOS)
print(f"放大 {scale}x: {new_size}")

# 处理颜色: 接近白色 → 透明(去白底),其余 → 纯白(深色 → 白色)
pixels = img.load()
nw, nh = img.size
for y in range(nh):
    for x in range(nw):
        r, g, b, a = pixels[x, y]
        brightness = (r + g + b) / 3
        if brightness > 240:
            # 白底 → 透明
            pixels[x, y] = (255, 255, 255, 0)
        else:
            # 深色(原图黑色图标和文字) → 改为白色
            pixels[x, y] = (255, 255, 255, 255)

img.save(dst, "PNG", optimize=True)
print(f"saved: {dst} ({os.path.getsize(dst)} bytes)")
print(f"Final size: {img.size}")
