"""
video_pipeline_v3.py — 科普视频生产线 v3
二次元风格 · 无任何文字 · FFmpeg zoompan 平滑运镜 · 多角度切换
"""
import asyncio, os, sys, io, json, subprocess, shutil, tempfile
from pathlib import Path

# 项目根目录（pipeline/ 的上一层）
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from moviepy import (
    ImageClip, AudioFileClip, VideoFileClip, CompositeVideoClip,
    concatenate_videoclips, vfx, TextClip, CompositeAudioClip
)
from moviepy.video.fx.Resize import Resize
from moviepy.video.fx.Crop import Crop
from moviepy.video.fx.FadeIn import FadeIn as VFadeIn
from moviepy.video.fx.FadeOut import FadeOut as VFadeOut
from moviepy.audio.fx.AudioFadeIn import AudioFadeIn
from moviepy.audio.fx.AudioFadeOut import AudioFadeOut
from moviepy.audio.fx.AudioLoop import AudioLoop
from moviepy.audio.fx.MultiplyVolume import MultiplyVolume
from PIL import Image
import edge_tts

# ============================================================
# 配置
# ============================================================
# 代理设置：从环境变量读取（国内用户需设置 HTTP_PROXY=http://127.0.0.1:7890）
_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
if _proxy:
    os.environ["HTTP_PROXY"] = _proxy
    os.environ["HTTPS_PROXY"] = _proxy

W, H = 1080, 1920
FPS = 24
VOICE = "zh-CN-YunxiNeural"
OUTPUT_DIR = PROJECT_ROOT / "output"
TMP_DIR = Path(tempfile.gettempdir()) / "deepspace_temp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = shutil.which("ffmpeg")
if not FFMPEG:
    print("❌ 找不到 ffmpeg！请安装后加入 PATH，或访问 https://ffmpeg.org/download.html")
    sys.exit(1)

# 开场钩子字体（系统自带黑体，无额外依赖）
HOOK_FONT = "C:/Windows/Fonts/simhei.ttf"
BGM_DIR = PROJECT_ROOT / "assets" / "bgm"


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


def _resolve_image(img_path):
    """解析图片路径：相对路径自动拼接项目根目录"""
    if not img_path:
        return None
    p = Path(img_path)
    if p.is_absolute():
        return img_path
    return str(PROJECT_ROOT / p)


# ============================================================
# BGM 生成（FFmpeg 合成环境音，无需外部音频文件）
# ============================================================

def generate_ambient_bgm(duration, output=None, mood="neutral"):
    """用 FFmpeg 合成简单的环境背景音。

    mood: "neutral" | "deep" | "uplift" | "mystery"
    返回 BGM 文件路径。
    """
    if output is None:
        output = str(TMP_DIR / f"bgm_ambient_{mood}.mp3")

    if os.path.exists(output):
        return output

    # 不同情绪对应不同频率和音色
    mood_config = {
        "neutral":  ("sine=frequency=220:duration={d},sine=frequency=330:duration={d}", 0.3),
        "deep":     ("sine=frequency=110:duration={d},sine=frequency=165:duration={d}", 0.35),
        "uplift":   ("sine=frequency=261:duration={d},sine=frequency=392:duration={d}", 0.25),
        "mystery":  ("sine=frequency=196:duration={d},sine=frequency=294:duration={d}", 0.28),
    }

    sine_def, target_vol = mood_config.get(mood, mood_config["neutral"])
    sine_def = sine_def.format(d=duration)

    # 生成双音叠加 + 淡入淡出
    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi", "-i",
        f"aevalsrc='0.3*sin(2*PI*220*t)+0.2*sin(2*PI*330*t)':s=44100:d={duration}",
        "-af", f"afade=t=in:d=2,afade=t=out:st={duration-3}:d=3,volume={target_vol}",
        "-c:a", "libmp3lame", "-q:a", "4",
        output
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=30)
        return output
    except Exception:
        return None


# ============================================================
# 主流程
# ============================================================

ZOOM_DIRECTIONS = ["in", "right", "out", "left", "up", "in", "left", "out"]


async def build_video(script_path):
    script_p = Path(script_path)
    if not script_p.is_absolute():
        script_p = PROJECT_ROOT / script_p
    with open(script_p, "r", encoding="utf-8") as f:
        script = json.load(f)

    title = script.get("title", "")
    scenes = script.get("scenes", [])
    voice = script.get("voice", VOICE)
    hook_text = script.get("hook", "")
    bgm_path = script.get("bgm", "")
    bgm_vol = script.get("bgm_volume", 0.15)

    print(f"==== {title} ====")
    print(f"场景: {len(scenes)} | 风格: 二次元 | 运镜: FFmpeg zoompan")
    if hook_text:
        print(f"开场钩子: {hook_text}")
    if bgm_path:
        print(f"BGM: {bgm_path}")

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

    # 开场钩子（前 3 秒 = 大字吸引眼球）
    first_img = _resolve_image(scenes[0].get("image_path", ""))
    if hook_text and first_img and os.path.exists(first_img) and os.path.exists(HOOK_FONT):
        hook_clip = ImageClip(first_img).resized((W, H)).with_duration(3.0)
        hook_txt = TextClip(
            text=hook_text, font=HOOK_FONT, font_size=72,
            color="white", stroke_color="black", stroke_width=4,
            method="caption", size=(W - 80, None), text_align="center"
        ).with_position("center").with_duration(3.0)
        hook_clip = CompositeVideoClip([hook_clip, hook_txt]).with_duration(3.0)
        hook_clip = hook_clip.with_effects([VFadeIn(0.3), VFadeOut(0.6)])
        clips.append(hook_clip)
        print(f"  钩子: 3.0s | \"{hook_text}\"")
    elif first_img and os.path.exists(first_img):
        intro = ImageClip(first_img).resized((W, H)).with_duration(2.0)
        intro = intro.with_effects([VFadeIn(1.0), VFadeOut(0.5)])
        clips.append(intro)
        print(f"  开场: 2.0s")

    # 场景片段
    for i, scene in enumerate(scenes):
        sid = scene["id"]
        ad = audio_data[i]
        img_path = _resolve_image(scene.get("image_path", ""))
        if not img_path:
            imgs = scene.get("images", [])
            if imgs:
                img_path = _resolve_image(imgs[0])

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
    last_img = _resolve_image(scenes[-1].get("image_path", ""))
    if last_img and os.path.exists(last_img):
        outro = ImageClip(last_img).resized((W, H)).with_duration(3.0)
        outro = outro.with_effects([VFadeIn(0.5), VFadeOut(1.5)])
        clips.append(outro)
        print(f"  结尾: 3.0s")

    # 拼接
    print(f"\n--- 合成 ---")
    video = concatenate_videoclips(clips, method="compose", padding=-0.5)
    print(f"  总时长: {video.duration:.0f}s")

    # BGM 背景音乐
    if bgm_path:
        bgm_p = Path(bgm_path)
        if not bgm_p.is_absolute():
            bgm_p = PROJECT_ROOT / bgm_p

        # 如果没有 BGM 文件，自动生成环境音
        if not bgm_p.exists():
            print(f"\n--- 生成 BGM ---")
            mood = script.get("bgm_mood", "neutral")
            generated = generate_ambient_bgm(
                int(video.duration) + 5, str(TMP_DIR / f"bgm_{title}.mp3"), mood
            )
            if generated:
                bgm_p = Path(generated)
                print(f"  已生成环境音: {mood}")
            else:
                print(f"  BGM 生成失败，跳过")

        if bgm_p.exists():
            print(f"  BGM: {bgm_p.name} (音量 {bgm_vol})")
            bgm_clip = AudioFileClip(str(bgm_p))
            if bgm_clip.duration < video.duration:
                bgm_clip = bgm_clip.with_effects([AudioLoop(duration=video.duration)])
            else:
                bgm_clip = bgm_clip.subclipped(0, video.duration)
            bgm_clip = bgm_clip.with_effects([
                MultiplyVolume(bgm_vol),
                AudioFadeIn(2.0),
                AudioFadeOut(3.0)
            ])

            # 混合配音 + BGM
            video_audio = video.audio
            mixed = CompositeAudioClip([video_audio, bgm_clip])
            video = video.with_audio(mixed)

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
