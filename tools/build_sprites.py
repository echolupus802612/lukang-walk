"""把 art/gen 里 Codex 画的 2x2 动作表切成横排精灵图 → docs/sprites/<动作>.webp

用法：python -I -B tools/build_sprites.py <项目根目录>

每张表 1024x1024，四格各 512。每帧：
  - 去背（若没有透明通道，抠掉纯绿 #00FF00）
  - 只留最大的一块连通区域，去掉杂点
  - 横向以「头部」中线对齐，纵向以脚底对齐（会跳的动作保留原本高度）
  - 放回 512 画布（脚底 y=490，中线 x=256），缩成 FRAME 像素
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageFilter

FRAME = 320
BASE_Y, MID_X, CELL = 490, 256, 512

# 动作 → (来源表, 用哪几格, 纵向对齐方式, 缩放)
# keepY：保留原本的高低（跳起来的帧）；第五项 "bbox"＝横向用整体外框置中（身体大幅倾斜的动作）
SHEETS = {
    "walk":      ("01_walk", [0, 1, 2, 3], "feet", 1.0),
    "idle":      ("02_idle", [0, 1, 2, 3], "feet", 1.0),
    "care":      ("03_care", [0, 1, 2, 3], "feet", 1.0),
    "cheer":     ("04_cheer", [0, 1, 2, 3], "keepY", 1.0),
    "pull":      ("05_pull", [0, 1, 2, 3], "feet", 1.0, "bbox"),
    "bye":       ("06_reluctant", [0, 1, 2, 3], "feet", 1.0),
    "point":     ("07_point", [0, 1], "feet", 1.0),
    "pointup":   ("07_point", [2, 3], "feet", 1.0),
}


def unkey(im):
    im = im.convert("RGBA")
    if im.getchannel("A").getextrema()[0] < 250:
        return im
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if g > 150 and r < 120 and b < 120:
                px[x, y] = (r, g, b, 0)
            elif g > r + 40 and g > b + 40:  # 绿边去溢色
                px[x, y] = (r, min(g, max(r, b)), b, a)
    return im


def largest_blob(im):
    """只保留不透明像素里最大的连通块（容忍 3px 缝隙，避免切掉尾巴尖）。"""
    a = im.getchannel("A").point(lambda v: 255 if v > 24 else 0)
    grown = a.filter(ImageFilter.MaxFilter(7))
    w, h = grown.size
    g = grown.load()
    seen = bytearray(w * h)
    best = None
    for sy in range(0, h, 2):
        for sx in range(0, w, 2):
            if g[sx, sy] == 0 or seen[sy * w + sx]:
                continue
            stack, pts = [(sx, sy)], []
            seen[sy * w + sx] = 1
            while stack:
                x, y = stack.pop()
                pts.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and g[nx, ny]:
                        seen[ny * w + nx] = 1
                        stack.append((nx, ny))
            if best is None or len(pts) > len(best):
                best = pts
    mask = Image.new("L", (w, h), 0)
    mp = mask.load()
    for x, y in best or []:
        mp[x, y] = 255
    out = im.copy()
    out.putalpha(Image.composite(im.getchannel("A"), Image.new("L", (w, h), 0), mask))
    return out


def head_center_x(im, bbox):
    """头部（bbox 上方 38%）不透明像素的横向重心。"""
    l, t, r, b = bbox
    band = im.getchannel("A").crop((l, t, r, t + int((b - t) * 0.38)))
    px, tot, sx = band.load(), 0, 0
    for y in range(band.height):
        for x in range(band.width):
            if px[x, y] > 128:
                tot += 1
                sx += x
    return l + (sx / tot if tot else band.width / 2)


def build(root):
    gen, out = root / "art" / "gen", root / "docs" / "sprites"
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, (src, cells, mode, scale, *xm) in SHEETS.items():
        if not (gen / f"{src}.png").exists():
            print(f"{name:8s} 缺 {src}.png，略过")
            continue
        sheet = unkey(Image.open(gen / f"{src}.png"))
        if sheet.size != (1024, 1024):
            sheet = sheet.resize((1024, 1024), Image.LANCZOS)
        frames, info = [], []
        for i in cells:
            cx, cy = (i % 2) * CELL, (i // 2) * CELL
            cell = largest_blob(sheet.crop((cx, cy, cx + CELL, cy + CELL)))
            bbox = cell.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
            hx = (bbox[0] + bbox[2]) / 2 if xm == ["bbox"] else head_center_x(cell, bbox)
            dx = MID_X - hx
            dy = BASE_Y - bbox[3] if mode == "feet" else 0
            canvas = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
            canvas.alpha_composite(cell, (round(dx), round(dy)))
            if scale != 1.0:
                s = canvas.resize((round(CELL * scale),) * 2, Image.LANCZOS)
                canvas = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
                canvas.alpha_composite(s, (round(MID_X - MID_X * scale), round(BASE_Y - BASE_Y * scale)))
            frames.append(canvas.resize((FRAME, FRAME), Image.LANCZOS))
            info.append({"cell": i, "bbox": bbox, "dx": round(dx), "dy": round(dy)})
        strip = Image.new("RGBA", (FRAME * len(frames), FRAME), (0, 0, 0, 0))
        for k, f in enumerate(frames):
            strip.alpha_composite(f, (k * FRAME, 0))
        path = out / f"{name}.webp"
        strip.save(path, "WEBP", quality=86, method=6)
        report[name] = {"frames": len(frames), "kb": path.stat().st_size // 1024, "cells": info}
        print(f"{name:8s} {len(frames)} 帧 {path.stat().st_size // 1024} KB", [(c["dx"], c["dy"]) for c in info])
    (root / "art" / "sprites_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    build(Path(sys.argv[1]))
