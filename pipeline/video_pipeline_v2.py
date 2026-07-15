"""
📚 学习参考 — 这是 v2 版本（已被 v3 取代）
展示了工程化演进：JSON 脚本分离、情感 TTS 控制、长文本拆句分段
请勿直接运行（含硬编码路径），阅读代码了解架构即可
详见仓库根目录 EVOLUTION.md

video_pipeline_v2.py — 科普视频生产线
Script-First 架构：结构化脚本 → 场景级SSML配音 → 精确音画同步 → MP4
"""
import asyncio
import json
import os
import sys
import io
import subprocess
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from moviepy import (
    ImageClip, AudioFileClip, CompositeVideoClip, TextClip,
    concatenate_videoclips, vfx, afx
)
from moviepy.video.fx.Resize import Resize
from moviepy.video.fx.Crop import Crop
from moviepy.video.fx.FadeIn import FadeIn as VFadeIn
from moviepy.video.fx.FadeOut import FadeOut as VFadeOut
from moviepy.audio.fx.AudioFadeIn import AudioFadeIn
from moviepy.audio.fx.AudioFadeOut import AudioFadeOut
from PIL import Image
import edge_tts
import edge_tts.communicate as comm

# ============================================================
# 配音引擎（用 rate/pitch/volume 控制情感，无需 SSML）
# ============================================================

# ============================================================
# 代理配置（必须在导入 edge_tts 前设好，aiohttp 读取环境变量）
# ============================================================
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"

# ============================================================
# 配置
# ============================================================
W, H = 1080, 1920
FPS = 24
VOICE = "zh-CN-YunxiNeural"
VOICE_NAME = "Microsoft Server Speech Text to Speech Voice (zh-CN, YunxiNeural)"
OUTPUT_DIR = Path("F:/claude/deepseek/1/output")
ASSETS_DIR = Path("F:/claude/deepseek/1/assets")
TMP_DIR = Path("F:/tmp/video_v2")
TMP_DIR.mkdir(parents=True, exist_ok=True)

PROXY = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}


# ============================================================
# SSML 配音引擎
# ============================================================

async def generate_scene_audio(narration, scene_id, voice=VOICE, rate="+0%", pitch="+0Hz", volume="+0%"):
    """为一个场景生成配音，返回 (音频路径, 精确时长秒数)

    情感控制参数：
    - rate: 语速，如 "+5%"（快）/ "-10%"（慢）
    - pitch: 音高，如 "+10Hz"（激昂）/ "-5Hz"（低沉）
    - volume: 音量，如 "+10%"（强调）/ "-5%"（轻声）
    """
    audio_path = str(TMP_DIR / f"scene_{scene_id:02d}.mp3")

    # 如果已有缓存配音，直接复用
    if os.path.exists(audio_path):
        clip = AudioFileClip(audio_path)
        duration = clip.duration
        clip.close()
        if duration > 0:
            return audio_path, duration

    # 长文本拆分（Microsoft TTS 对超长文本可能返回空）
    sentences = narration.replace('！', '！|').replace('？', '？|').replace('。', '。|').split('|')
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) <= 2:
        # 短文本直接合成
        for attempt in range(3):
            try:
                communicate = edge_tts.Communicate(narration, voice, rate=rate, pitch=pitch, volume=volume)
                await communicate.save(audio_path)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(3)
    else:
        # 长文本分段合成，再拼接
        import tempfile
        parts = []
        for i in range(0, len(sentences), 2):
            chunk = '。'.join(sentences[i:i+2]) + '。'
            tmp_path = str(TMP_DIR / f"scene_{scene_id:02d}_p{i}.mp3")
            for attempt in range(3):
                try:
                    c = edge_tts.Communicate(chunk, voice, rate=rate, pitch=pitch, volume=volume)
                    await c.save(tmp_path)
                    parts.append(AudioFileClip(tmp_path))
                    break
                except Exception as e:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(3)

        # 拼接所有片段
        if parts:
            from moviepy import concatenate_audioclips
            merged = concatenate_audioclips(parts)
            merged.write_audiofile(audio_path)
            for p in parts:
                p.close()

    clip = AudioFileClip(audio_path)
    duration = clip.duration
    clip.close()
    return audio_path, duration


# ============================================================
# 视频片段合成
# ============================================================

def make_title_card(text, duration, bg_image=None):
    """标题卡片"""
    bg_path = bg_image or str(ASSETS_DIR / "ai" / "title_bg.png")
    if not os.path.exists(bg_path):
        # 用已有的任意图
        for f in (ASSETS_DIR / "ai").glob("*.png"):
            bg_path = str(f)
            break
    if not os.path.exists(bg_path):
        bg_path = "F:/tmp/pillars_of_creation.png"

    clip = ImageClip(bg_path).resized((W, H))
    txt = TextClip(
        text=text, font="C:/Windows/Fonts/msyhbd.ttc", font_size=64,
        color="white", stroke_color="black", stroke_width=4,
        method="caption", size=(W - 80, None), text_align="center"
    ).with_position("center").with_duration(duration)
    return CompositeVideoClip([clip, txt]).with_duration(duration)


def make_scene(image_path, audio_path, duration, subtitle="", zoom="none"):
    """制作一个场景片段：图片 + 配音 + 纯字幕（底部白色小字）"""
    # 图片（带 Ken Burns 缩放）
    if zoom == "zoom_in_slow":
        scale = 1.08
        clip = ImageClip(image_path).resized((int(W * scale), int(H * scale)))
        clip = clip.with_effects([
            Crop(x_center=W/2, y_center=H/2, width=W, height=H)
        ])
    elif zoom == "wide":
        clip = ImageClip(image_path).resized((W, H))
    else:
        clip = ImageClip(image_path).resized((W, H))

    clip = clip.with_duration(duration)
    clip = clip.with_effects([VFadeIn(0.3), VFadeOut(0.3)])

    # 配音
    audio = AudioFileClip(audio_path)
    if audio.duration < duration:
        duration = audio.duration
    audio = audio.subclipped(0, duration)
    audio = audio.with_effects([AudioFadeIn(0.15), AudioFadeOut(0.3)])

    clip = clip.with_duration(duration)

    # 纯字幕（底部，配音内容）
    if subtitle:
        txt = TextClip(
            text=subtitle, font="C:/Windows/Fonts/msyh.ttc", font_size=36,
            color="white", stroke_color="black", stroke_width=2,
            method="caption", size=(W - 100, None)
        ).with_position(("center", H * 0.85)).with_duration(duration)
        clip = CompositeVideoClip([clip, txt]).with_duration(duration)

    # 设置音频
    clip = clip.with_audio(audio)
    return clip


def make_outro_card(text, duration, bg_image=None):
    """结束卡片"""
    bg_path = bg_image or "F:/tmp/pillars_wide.png"
    return make_title_card(text, duration, bg_path)


# ============================================================
# 图片预处理
# ============================================================

def prepare_image(path_or_url, scene_id):
    """确保图片是 1080×1920 竖屏格式"""
    if path_or_url.startswith("http"):
        # 下载
        import requests
        sess = requests.Session()
        sess.proxies.update(PROXY)
        fname = f"scene_{scene_id:02d}{Path(path_or_url).suffix or '.jpg'}"
        local = str(ASSETS_DIR / "web" / fname)
        os.makedirs(str(ASSETS_DIR / "web"), exist_ok=True)
        r = sess.get(path_or_url, timeout=30)
        with open(local, "wb") as f:
            f.write(r.content)
        path_or_url = local

    if not path_or_url or not os.path.exists(path_or_url):
        return None

    # 裁切为竖屏
    img = Image.open(path_or_url)
    iw, ih = img.size
    if iw == W and ih == H:
        return path_or_url

    # 缩放 + 中心裁切
    ratio = max(W / iw, H / ih)
    new_w, new_h = int(iw * ratio), int(ih * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - W) // 2
    top = (new_h - H) // 2
    img = img.crop((left, top, left + W, top + H))

    out_path = str(ASSETS_DIR / "processed" / f"scene_{scene_id:02d}.png")
    os.makedirs(str(ASSETS_DIR / "processed"), exist_ok=True)
    img.save(out_path)
    return out_path


# ============================================================
# 主流程
# ============================================================

async def build_video(script_path, dry_run=False):
    """主入口：读取 JSON 脚本 → 生成配音 → 合成视频"""

    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    title = script.get("title", "未命名")
    scenes = script.get("scenes", [])
    voice = script.get("voice", VOICE)
    voice_name = script.get("voice_name", VOICE_NAME)

    print(f"==== {title} ====")
    print(f"场景数: {len(scenes)}")
    print(f"配音: {voice}")

    # Phase 1：生成所有场景配音
    print("\n--- Phase 1: 配音生成 ---")
    audio_data = []
    for scene in scenes:
        sid = scene["id"]
        narration = scene["narration"]
        rate = scene.get("rate", "+0%")
        pitch = scene.get("pitch", "+0Hz")
        volume = scene.get("volume", "+0%")
        print(f"  场景{sid} 配音中... [rate={rate}, pitch={pitch}]")
        audio_path, duration = await generate_scene_audio(
            narration, sid, voice, rate=rate, pitch=pitch, volume=volume
        )
        audio_data.append({"id": sid, "path": audio_path, "duration": duration})
        print(f"    时长: {duration:.1f}s | {narration[:50]}...")

    # Phase 2：准备图片
    print("\n--- Phase 2: 图片准备 ---")
    image_paths = []
    for scene in scenes:
        sid = scene["id"]
        img = scene.get("image_path", "")
        if not img:
            # 尝试从 assets 目录找
            for d in ["nasa", "ai", "web"]:
                candidates = list((ASSETS_DIR / d).glob(f"*{sid:02d}*")) + \
                             list((ASSETS_DIR / d).glob(f"scene_{sid:02d}*"))
                if candidates:
                    img = str(candidates[0])
                    break
        if img and os.path.exists(img):
            processed = prepare_image(img, sid)
            image_paths.append(processed or img)
            print(f"  场景{sid}: {img}")
        else:
            # 兜底
            fallback = f"F:/tmp/pillars_of_creation.png"
            if os.path.exists(fallback):
                image_paths.append(fallback)
                print(f"  场景{sid}: [兜底] {fallback}")
            else:
                image_paths.append(None)
                print(f"  场景{sid}: ⚠️ 无图片")

    # Phase 3：合成
    print(f"\n--- Phase 3: 视频合成 ---")
    clips = []

    # 标题卡
    title_dur = script.get("title_duration", 2.5)
    title_bg = image_paths[0] if image_paths else None
    clips.append(make_title_card(title, title_dur, title_bg))
    print(f"  标题卡: {title_dur}s")

    # 场景片段
    for i, scene in enumerate(scenes):
        sid = scene["id"]
        ad = audio_data[i]
        zoom = scene.get("zoom", "none")
        subtitle = scene.get("subtitle", scene.get("narration", "")[:60])
        img_path = image_paths[i] if i < len(image_paths) else None

        if not img_path or not os.path.exists(img_path):
            print(f"  场景{sid}: 跳过（无图片）")
            continue

        clip = make_scene(img_path, ad["path"], ad["duration"], subtitle, zoom)
        clips.append(clip)
        print(f"  场景{sid}: {ad['duration']:.1f}s | {subtitle}")

    # 结束卡
    outro_dur = script.get("outro_duration", 2.5)
    outro_text = script.get("outro_text", "期待下次再见")
    clips.append(make_outro_card(outro_text, outro_dur, image_paths[-1] if image_paths else None))
    print(f"  结束卡: {outro_dur}s")

    # 拼接 + 过渡
    video = concatenate_videoclips(clips, method="compose", padding=-0.5)
    print(f"  总时长: {video.duration:.1f}s")

    if dry_run:
        print("\n[Dry Run] 未导出视频")
        return video

    # 导出
    out_name = script.get("output", f"{title}.mp4")
    out_path = str(OUTPUT_DIR / out_name)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n  渲染中... → {out_path}")
    video.write_videofile(
        out_path, fps=FPS, codec="libx264",
        audio_codec="aac", preset="medium", bitrate="6000k"
    )
    print(f"==== 完成! ====")
    print(f"文件: {out_path}")
    return video


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python video_pipeline_v2.py <脚本.json> [--dry-run]")
        sys.exit(1)

    script_file = sys.argv[1]
    is_dry = "--dry-run" in sys.argv
    asyncio.run(build_video(script_file, dry_run=is_dry))
