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
# 自动检测 imageio_ffmpeg 自带的 ffmpeg（Python 包内置，无需额外安装）
if not FFMPEG:
    try:
        import imageio_ffmpeg
        FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
if not FFMPEG:
    # 最后尝试常见路径
    for guess in [
        "ffmpeg-win-x86_64-v7.1.exe",  # imageio_ffmpeg 默认文件名
    ]:
        g = shutil.which(guess)
        if g:
            FFMPEG = g
            break
if not FFMPEG:
    print("❌ 找不到 ffmpeg！请安装后加入 PATH，或访问 https://ffmpeg.org/download.html")
    sys.exit(1)

# 开场钩子字体（系统自带黑体，无额外依赖）
HOOK_FONT = "C:/Windows/Fonts/simhei.ttf"
BGM_DIR = PROJECT_ROOT / "assets" / "bgm"


# ============================================================
# FFmpeg Zoompan — CPU 平滑 Ken Burns
# ============================================================

# 色彩预设（FFmpeg eq 滤镜参数）
COLOR_PRESETS = {
    "warm":  "eq=brightness=0.03:saturation=1.2",
    "cool":  "eq=brightness=-0.02:saturation=0.85",
    "vivid": "eq=saturation=1.35:contrast=1.1",
    "film":  "eq=contrast=1.15:saturation=1.1:brightness=-0.02",
}


def ffmpeg_zoompan(image_path, duration, direction="in", color=None, output=None):
    """用 FFmpeg zoompan 生成平滑缩放片段（纯 CPU，不需要 GPU）

    direction: "in" | "out" | "left" | "right" | "up" | "down"
    color: "warm" | "cool" | "vivid" | "film" | None（不调色）
    """
    if output is None:
        tag = f"{direction}_{color}" if color else direction
        output = str(TMP_DIR / f"zoom_{Path(image_path).stem}_{tag}.mp4")

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

    # 基础 zoompan 滤镜
    vf = f"zoompan=z='{expr}':x='{x_expr}':y='{y_expr}':d={total_frames}:s={W}x{H}:fps={FPS}"
    # 叠加色彩滤镜
    if color and color in COLOR_PRESETS:
        vf += f",{COLOR_PRESETS[color]}"

    cmd = [
        FFMPEG, "-y", "-loop", "1", "-i", image_path,
        "-vf", vf,
        "-t", str(duration), "-pix_fmt", "yuv420p", output
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)
    return output


def ffmpeg_compare(img_a, img_b, duration, output=None):
    """分屏对比：两张图并排展示（适合体型对比、数据对比）"""
    if output is None:
        output = str(TMP_DIR / f"compare_{Path(img_a).stem}_{Path(img_b).stem}.mp4")

    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-i", img_a,
        "-loop", "1", "-i", img_b,
        "-filter_complex",
        f"[0:v]scale={W//2}:{H},setsar=1[L];"
        f"[1:v]scale={W//2}:{H},setsar=1[R];"
        f"[L][R]hstack=inputs=2,"
        f"zoompan=z='1.02':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration*FPS)}:s={W}x{H}:fps={FPS}",
        "-t", str(duration), "-pix_fmt", "yuv420p", output
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)
    return output


def make_image_clip(image_path, duration, zoom_direction="in", color=None):
    """创建带 zoompan 效果的图片片段"""
    video_path = ffmpeg_zoompan(image_path, duration, zoom_direction, color)
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
# 音效生成（FFmpeg 合成短促效果音）
# ============================================================

def generate_sfx(sfx_type, output=None):
    """用 FFmpeg 合成短音效。sfx_type: ding | whoosh | boom | tick"""
    if output is None:
        output = str(TMP_DIR / f"sfx_{sfx_type}.mp3")

    if os.path.exists(output):
        return output

    sfx_config = {
        "ding":   "aevalsrc='0.6*sin(2*PI*1200*t)*exp(-8*t)':s=44100:d=0.6",
        "whoosh": "aevalsrc='0.4*sin(2*PI*(400+800*t)*t)*exp(-3*t)':s=44100:d=0.8",
        "boom":   "aevalsrc='0.8*sin(2*PI*80*t)*exp(-2*t)':s=44100:d=1.0",
        "tick":   "aevalsrc='0.5*sin(2*PI*800*t)*exp(-15*t)':s=44100:d=0.3",
    }

    expr = sfx_config.get(sfx_type, sfx_config["ding"])

    cmd = [
        FFMPEG, "-y", "-f", "lavfi", "-i", expr,
        "-c:a", "libmp3lame", "-q:a", "2", output
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=10)
        return output if os.path.exists(output) else None
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

    # Phase 1: 配音（含节奏控制：pace 字段映射为语速）
    print("\n--- 配音 ---")
    PACE_RATE_MAP = {"slow": "-8%", "normal": "+0%", "fast": "+8%"}
    audio_data = []
    for scene in scenes:
        sid = scene["id"]
        # 节奏控制：slow/fast → 语速调整
        pace = scene.get("pace", "normal")
        base_rate = scene.get("rate", "+0%")
        pace_adjust = PACE_RATE_MAP.get(pace, "+0%")

        # 合并 rate 值（简单叠加百分比）
        def _merge_rate(r1, r2):
            v1 = int(r1.replace("%", "").replace("+", ""))
            v2 = int(r2.replace("%", "").replace("+", "")) if r2 else 0
            v = v1 + v2
            return f"{'+' if v >= 0 else ''}{v}%"

        effective_rate = _merge_rate(base_rate, pace_adjust)
        audio_path, dur = await generate_scene_audio(
            scene["narration"], sid, voice,
            effective_rate, scene.get("pitch", "+0Hz")
        )
        audio_data.append({"id": sid, "path": audio_path, "duration": dur})
        pace_mark = f" [{pace}]" if pace != "normal" else ""
        print(f"  S{sid}: {dur:.1f}s | rate={effective_rate}{pace_mark}")

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
    global_color = script.get("color", "")  # 全局色彩预设

    for i, scene in enumerate(scenes):
        sid = scene["id"]
        ad = audio_data[i]
        direction = scene.get("zoom", ZOOM_DIRECTIONS[i % len(ZOOM_DIRECTIONS)])
        color = scene.get("color", global_color) or None  # 场景级优先
        layout = scene.get("layout", "")
        imgs = scene.get("images", [])
        img_path = _resolve_image(scene.get("image_path", ""))
        if not img_path and imgs:
            img_path = _resolve_image(imgs[0])

        if not img_path or not os.path.exists(img_path):
            print(f"  S{sid}: 跳过(无图)")
            continue

        # 分屏对比模式
        if layout == "compare":
            img_b = _resolve_image(scene.get("image_compare", ""))
            if img_b and os.path.exists(img_b):
                video_path = ffmpeg_compare(img_path, img_b, ad["duration"])
                clip = VideoFileClip(video_path)
                clip = clip.with_effects([VFadeIn(0.4), VFadeOut(0.4)])
                clip = clip.with_duration(ad["duration"])
            else:
                clip = make_image_clip(img_path, ad["duration"], direction, color)

        # 多图交替：2+ 张图轮播
        elif len(imgs) >= 2:
            sub_dur = ad["duration"] / len(imgs)
            sub_clips = []
            for j, imp in enumerate(imgs):
                resolved = _resolve_image(imp)
                if resolved and os.path.exists(resolved):
                    sc = make_image_clip(resolved, sub_dur, direction, color)
                    sub_clips.append(sc)
            if sub_clips:
                clip = concatenate_videoclips(sub_clips, method="compose", padding=-0.3)
                clip = clip.with_duration(ad["duration"])
            else:
                clip = make_image_clip(img_path, ad["duration"], direction, color)

        else:
            clip = make_image_clip(img_path, ad["duration"], direction, color)

        # 配音
        audio = AudioFileClip(ad["path"])
        if audio.duration > ad["duration"]:
            audio = audio.subclipped(0, ad["duration"])
        audio = audio.with_effects([AudioFadeIn(0.15), AudioFadeOut(0.5)])

        # 音效（可选）
        sfx_type = scene.get("sfx", "")
        if sfx_type:
            sfx_path = generate_sfx(sfx_type)
            if sfx_path:
                sfx = AudioFileClip(sfx_path)
                sfx = sfx.with_effects([MultiplyVolume(0.3)])
                audio = CompositeAudioClip([audio, sfx])

        # 日志
        tags = []
        if layout == "compare":
            tags.append("分屏对比")
        if color:
            tags.append(f"色调={color}")
        if len(imgs) >= 2:
            tags.append(f"{len(imgs)}图交替")
        if sfx_type:
            tags.append(f"sfx={sfx_type}")
        tag_str = (" | " + " · ".join(tags)) if tags else ""
        print(f"  S{sid}: {ad['duration']:.1f}s | zoom={direction}{tag_str}")

        clip = clip.with_audio(audio)
        clips.append(clip)

        clip = clip.with_audio(audio)
        clips.append(clip)

    # 结尾：最后一张图 fade out（含互动话术 CTA）
    outro_text = script.get("outro_narration", "")
    last_img = _resolve_image(scenes[-1].get("image_path", ""))
    if last_img and os.path.exists(last_img):
        outro_duration = 3.0
        outro_audio = None

        # 如果有结尾话术，生成配音
        if outro_text:
            cta_path, cta_dur = await generate_scene_audio(
                outro_text, 99, voice, "-3%", "-2Hz"
            )
            outro_duration = max(3.0, cta_dur + 1.5)
            outro_audio = AudioFileClip(cta_path)
            if outro_audio.duration > outro_duration:
                outro_audio = outro_audio.subclipped(0, outro_duration)
            outro_audio = outro_audio.with_effects([AudioFadeIn(0.3), AudioFadeOut(1.2)])
            print(f"  结尾CTA: \"{outro_text[:40]}...\" ({cta_dur:.1f}s)")

        outro = ImageClip(last_img).resized((W, H)).with_duration(outro_duration)
        outro = outro.with_effects([VFadeIn(0.5), VFadeOut(1.5)])
        if outro_audio:
            outro = outro.with_audio(outro_audio)
        clips.append(outro)
        print(f"  结尾画面: {outro_duration:.1f}s")

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
