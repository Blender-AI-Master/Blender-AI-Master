"""处理 Blender-AI Master logo:
1. 去底(白色 → 透明)
2. 整体颜色(深色) → 白色
3. 输出到插件资源目录
"""
import os
from PIL import Image

src = r"C:\Users\Administrator\Desktop\jietu\12.png"
dst_dir = r"I:\Projects-2026\CLI-Anything-Blender\resources\branding"
os.makedirs(dst_dir, exist_ok=True)

img = Image.open(src).convert("RGBA")
pixels = img.load()
w, h = img.size

# 阈值:白色/近白 → 透明;深色 → 白色
for y in range(h):
    for x in range(w):
        r, g, b, a = pixels[x, y]
        # 计算亮度
        brightness = (r + g + b) / 3
        if brightness > 240:
            # 近白色 → 透明
            pixels[x, y] = (255, 255, 255, 0)
        else:
            # 深色 → 纯白
            pixels[x, y] = (255, 255, 255, 255)

# 保存为透明 PNG
out_path = os.path.join(dst_dir, "blender-ai-wordmark-white.png")
img.save(out_path, "PNG")
print(f"saved: {out_path}, size={img.size}")

# 也备份一份到 desktop 便于查看
img.save(r"C:\Users\Administrator\Desktop\logo-white-preview.png", "PNG")
print("preview saved to desktop")
