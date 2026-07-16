"""
video_pipeline_v3.py — 科普视频生产线 v3
二次元风格 · 无任何文字 · FFmpeg zoompan 平滑运镜 · 多角度切换
"""
import asyncio, os, sys, io, json, subprocess, shutil
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from moviepy import (
    ImageClip, AudioFileClip, VideoFileClip, CompositeVideoClip,
    concatenate_videoclips, vfx
)
from moviepy.video.fx.Resize import Resize
from moviepy.video.fx.Crop import Crop
from moviepy.video.fx.FadeIn import FadeIn as VFadeIn
from moviepy.video.fx.FadeOut import FadeOut as VFadeOut
from moviepy.audio.fx.AudioFadeIn import AudioFadeIn
from moviepy.audio.fx.AudioFadeOut import AudioFadeOut
from moviepy.audio.fx.AudioLoop import AudioLoop
from PIL import Image
import edge_tts

# ============================================================
# 配置
# ============================================================
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"
os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"

W, H = 1080, 1920
FPS = 24
VOICE = "zh-CN-YunxiNeural"
OUTPUT_DIR = Path("F:/claude/deepseek/1/output")
TMP_DIR = Path("F:/tmp/video_v3")
TMP_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = shutil.which("ffmpeg") or str(Path(
    "C:/Users/26032/AppData/Local/Programs/Python/Python312/Lib/site-packages/"
    "imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe"
))


# ============================================================
# FFmpeg Zoompan — CPU 平滑 Ken Burns
# ============================================================

def ffmpeg_zoompan(image_path, duration, direction="in", output=None):
    """用 FFmpeg zoompan 生成平滑缩放片段（纯 CPU，不需要 GPU）

    direction: "in" | "out" | "left" | "right" | "up" | "down"
    """
    if output is None:
        output = str(TMP_DIR / f"zoom_{Path(image_path).stem}_{direction}.mp4")

    if direction == "in":
        expr = "zoom+0.0008"
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif direction == "out":
        expr = "1.08-0.0008*on"
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif direction == "right":
        expr = "1.04"
        x_expr = "iw/2-(iw/zoom/2)+2*on"
        y_expr = "ih/2-(ih/zoom/2)"
    elif direction == "left":
        expr = "1.04"
        x_expr = "iw/2-(iw/zoom/2)-2*on"
        y_expr = "ih/2-(ih/zoom/2)"
    elif direction == "up":
        expr = "1.04"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)-2*on"
    else:  # down
        expr = "1.04"
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)+2*on"

    total_frames = int(duration * FPS)

    cmd = [
        FFMPEG, "-y", "-loop", "1", "-i", image_path,
        "-vf", f"zoompan=z='{expr}':x='{x_expr}':y='{y_expr}':d={total_frames}:s={W}x{H}:fps={FPS}",
        "-t", str(duration), "-pix_fmt", "yuv420p", output
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)
    return output


def make_image_clip(image_path, duration, zoom_direction="in"):
    """创建带 zoompan 效果的图片片段"""
    video_path = ffmpeg_zoompan(image_path, duration, zoom_direction)
    clip = VideoFileClip(video_path)
    clip = clip.with_effects([VFadeIn(0.4), VFadeOut(0.4)])
    return clip.with_duration(duration)


# ============================================================
# 配音引擎
# ============================================================

async def generate_scene_audio(narration, scene_id, voice=VOICE, rate="+0%", pitch="+0Hz"):
    import hashlib
    text_hash = hashlib.md5(narration.encode()).hexdigest()[:8]
    audio_path = str(TMP_DIR / f"scene_{scene_id:02d}_{text_hash}.mp3")
    if os.path.exists(audio_path):
        clip = AudioFileClip(audio_path)
        dur = clip.duration
        clip.close()
        if dur > 0:
            return audio_path, dur

    for attempt in range(5):
        try:
            c = edge_tts.Communicate(narration, voice, rate=rate, pitch=pitch)
            await c.save(audio_path)
            clip = AudioFileClip(audio_path)
            dur = clip.duration
            clip.close()
            return audio_path, dur
        except Exception as e:
            if attempt == 4:
                raise
            await asyncio.sleep(5)


# ============================================================
# 主流程
# ============================================================

ZOOM_DIRECTIONS = ["in", "right", "out", "left", "up", "in", "left", "out"]


async def build_video(script_path):
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    title = script.get("title", "")
    scenes = script.get("scenes", [])
    voice = script.get("voice", VOICE)

    print(f"==== {title} ====")
    print(f"场景: {len(scenes)} | 风格: 二次元 | 文字: 无 | 运镜: FFmpeg zoompan")

    # Phase 1: 配音
    print("\n--- 配音 ---")
    audio_data = []
    for scene in scenes:
        sid = scene["id"]
        audio_path, dur = await generate_scene_audio(
            scene["narration"], sid, voice,
            scene.get("rate", "+0%"), scene.get("pitch", "+0Hz")
        )
        audio_data.append({"id": sid, "path": audio_path, "duration": dur})
        print(f"  S{sid}: {dur:.1f}s")

    # Phase 2: 图片准备 + FFmpeg zoompan 片段
    print("\n--- 视频片段 ---")
    clips = []

    # 开场：第一张图 fade in
    first_img = scenes[0].get("image_path", scenes[0].get("images", [None])[0])
    if first_img and os.path.exists(first_img):
        intro = ImageClip(first_img).resized((W, H)).with_duration(2.0)
        intro = intro.with_effects([VFadeIn(1.0), VFadeOut(0.5)])
        clips.append(intro)
        print(f"  开场: 2.0s")

    # 场景片段
    for i, scene in enumerate(scenes):
        sid = scene["id"]
        ad = audio_data[i]
        img_path = scene.get("image_path", "")
        if not img_path:
            imgs = scene.get("images", [])
            if imgs:
                img_path = imgs[0]

        if not img_path or not os.path.exists(img_path):
            print(f"  S{sid}: 跳过(无图)")
            continue

        direction = scene.get("zoom", ZOOM_DIRECTIONS[i % len(ZOOM_DIRECTIONS)])
        clip = make_image_clip(img_path, ad["duration"], direction)
        audio = AudioFileClip(ad["path"])
        if audio.duration > ad["duration"]:
            audio = audio.subclipped(0, ad["duration"])
        audio = audio.with_effects([AudioFadeIn(0.15), AudioFadeOut(0.5)])
        clip = clip.with_audio(audio)
        clips.append(clip)
        print(f"  S{sid}: {ad['duration']:.1f}s | zoom={direction}")

    # 结尾：最后一张图 fade out
    last_img = scenes[-1].get("image_path", "")
    if last_img and os.path.exists(last_img):
        outro = ImageClip(last_img).resized((W, H)).with_duration(3.0)
        outro = outro.with_effects([VFadeIn(0.5), VFadeOut(1.5)])
        clips.append(outro)
        print(f"  结尾: 3.0s")

    # 拼接
    print(f"\n--- 合成 ---")
    video = concatenate_videoclips(clips, method="compose", padding=-0.5)
    print(f"  总时长: {video.duration:.0f}s")

    out_name = script.get("output", f"{title}.mp4")
    out_path = str(OUTPUT_DIR / out_name)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    video.write_videofile(out_path, fps=FPS, codec="libx264", audio_codec="aac", preset="medium", bitrate="6000k")
    print(f"==== 完成: {out_path} ====")
    return video


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python video_pipeline_v3.py <脚本.json>")
        sys.exit(1)
    asyncio.run(build_video(sys.argv[1]))
