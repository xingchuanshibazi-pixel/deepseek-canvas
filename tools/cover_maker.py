"""
cover_maker.py — 小红书/抖音竖版封面生成器

从脚本 JSON + 第一张图片 → 生成 3:4 竖版大字封面
用法：python tools/cover_maker.py scripts/巨齿鲨_v3.json [输出路径]
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import json

# 项目根
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# 封面尺寸（小红书 3:4 竖版）
COVER_W, COVER_H = 1080, 1440

# 字体（按优先级尝试）
FONT_CANDIDATES = [
    "C:/Windows/Fonts/simhei.ttf",   # 黑体
    "C:/Windows/Fonts/msyhbd.ttc",   # 微软雅黑粗体
    "C:/Windows/Fonts/simkai.ttf",   # 楷体
]


def _find_font(size):
    for fp in FONT_CANDIDATES:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def _resolve_path(img_path):
    p = Path(img_path)
    if p.is_absolute():
        return str(p)
    return str(PROJECT_ROOT / p)


def make_cover(script_path, output_path=None):
    """从脚本生成封面图"""
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    title = script.get("title", "未命名")
    hook = script.get("hook", "")
    scenes = script.get("scenes", [])

    # 封面主图 = 第一张场景图
    if not scenes:
        print("❌ 脚本无场景")
        return None

    first_img = _resolve_path(scenes[0].get("image_path", ""))
    if not os.path.exists(first_img):
        print(f"❌ 找不到图片: {first_img}")
        return None

    # 打开背景图，裁切为 3:4
    bg = Image.open(first_img).convert("RGBA")
    iw, ih = bg.size

    # 裁切/缩放为 1080×1440
    target_ratio = COVER_W / COVER_H
    img_ratio = iw / ih

    if img_ratio > target_ratio:
        # 图片更宽，裁左右
        new_w = int(ih * target_ratio)
        left = (iw - new_w) // 2
        bg = bg.crop((left, 0, left + new_w, ih))
    else:
        # 图片更高，裁上下
        new_h = int(iw / target_ratio)
        top = (ih - new_h) // 2
        bg = bg.crop((0, top, iw, top + new_h))

    bg = bg.resize((COVER_W, COVER_H), Image.LANCZOS)

    # 底部渐变遮罩（增强文字可读性）
    overlay = Image.new("RGBA", (COVER_W, COVER_H), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    mask_height = COVER_H // 3
    for y in range(COVER_H - mask_height, COVER_H):
        alpha = int(180 * (y - (COVER_H - mask_height)) / mask_height)
        draw_overlay.rectangle([(0, y), (COVER_W, y + 1)], fill=(0, 0, 0, alpha))

    bg = Image.alpha_composite(bg, overlay)

    # 文字层
    draw = ImageDraw.Draw(bg)

    # 主标题（大号）
    title_font = _find_font(80)
    title_lines = _wrap_text(title, title_font, COVER_W - 120)
    title_y = COVER_H - mask_height + 40
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        tw = bbox[2] - bbox[0]
        draw.text(
            ((COVER_W - tw) // 2, title_y),
            line, font=title_font, fill=(255, 255, 255, 255),
            stroke_width=3, stroke_fill=(0, 0, 0, 200)
        )
        title_y += bbox[3] - bbox[1] + 8

    # 钩子文字（小一点，放在标题上方）
    if hook:
        hook_font = _find_font(44)
        hook_clean = hook.replace("\n", " · ")
        bbox = draw.textbbox((0, 0), hook_clean, font=hook_font)
        hw = bbox[2] - bbox[0]
        draw.text(
            ((COVER_W - hw) // 2, COVER_H - mask_height - 70),
            hook_clean, font=hook_font,
            fill=(255, 220, 100, 255),
            stroke_width=2, stroke_fill=(0, 0, 0, 180)
        )

    # 保存
    if output_path is None:
        output_path = PROJECT_ROOT / "output" / f"cover_{title}.png"

    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    bg = bg.convert("RGB")
    bg.save(str(out_p), quality=95)
    print(f"✅ 封面已生成: {out_p}")
    return str(out_p)


def _wrap_text(text, font, max_width):
    """简单按字符换行，超过宽度则折行"""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines if lines else [text]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python tools/cover_maker.py <脚本.json> [输出路径]")
        sys.exit(1)

    script = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    make_cover(script, out)
