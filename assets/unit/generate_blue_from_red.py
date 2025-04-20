import os
import sys
from PIL import Image
import numpy as np

"""
增加unit的时候，只需用红色绘制，命名为TYPE_0.png。然后运行这个脚本，即可自动生成蓝色的TYPE_1.png。
"""

def shift_hue(img, shift_deg):
    img = img.convert('RGBA')
    arr = np.array(img).astype('float32') / 255.0

    rgb = arr[..., :3]
    alpha = arr[..., 3:]

    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxc = np.max(rgb, axis=2)
    minc = np.min(rgb, axis=2)
    v = maxc

    s = (maxc - minc) / (maxc + 1e-6)

    h = np.zeros_like(r)
    mask = maxc == r
    h[mask] = (g[mask] - b[mask]) / (maxc[mask] - minc[mask] + 1e-6)
    mask = maxc == g
    h[mask] = 2.0 + (b[mask] - r[mask]) / (maxc[mask] - minc[mask] + 1e-6)
    mask = maxc == b
    h[mask] = 4.0 + (r[mask] - g[mask]) / (maxc[mask] - minc[mask] + 1e-6)
    h = (h / 6.0) % 1.0

    h = (h + shift_deg / 360.0) % 1.0

    i = (h * 6.0).astype('int')
    f = (h * 6.0) - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))

    r2 = np.choose(i % 6, [v, q, p, p, t, v])
    g2 = np.choose(i % 6, [t, v, v, q, p, p])
    b2 = np.choose(i % 6, [p, p, t, v, v, q])

    rgb_shifted = np.stack([r2, g2, b2], axis=2)
    rgba = np.concatenate([rgb_shifted, alpha], axis=2)
    rgba = (rgba * 255).astype('uint8')
    return Image.fromarray(rgba, mode='RGBA')

def process_folder(folder_path):
    for filename in os.listdir(folder_path):
        if filename.endswith('_0.png'):
            base = filename[:-6]
            if base+'_1.png' in os.listdir(folder_path):
                print(f"{base}_1.png already exists, skipping.")
                continue
            input_path = os.path.join(folder_path, filename)
            output_path = os.path.join(folder_path, f'{base}_1.png')

            print(f"Processing {filename} → {base}_1.png")

            img = Image.open(input_path)
            img = shift_hue(img, 220) # 色调偏转角度 -------------------------- [可调节]
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
            img.save(output_path)

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    process_folder(current_dir)