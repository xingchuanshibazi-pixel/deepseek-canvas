"""
📚 学习参考 — 这是最初原型（已被 v3 取代）
仅 ~130 行硬编码实现，最适合初学者阅读
请勿直接运行（含硬编码路径），阅读代码了解基本流程即可
详见仓库根目录 EVOLUTION.md

深空画布 - 视频生成器 原型
从静态图片 + 配音合成小红书竖屏视频
"""
import asyncio
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from moviepy import (
    ImageClip, AudioFileClip, CompositeVideoClip, TextClip,
    concatenate_videoclips
)
import edge_tts

VOICEOVER_TEXT = """
距离地球6500光年，这里是创生之柱。
韦伯望远镜拍到了它，但那不是真的颜色。
红外波段的数据被科学家加了伪彩色，我们肉眼飞过去，永远看不到那个样子。
所以我用AI按照可见光波段重新渲染了一版。
左边最小的柱子有四光年长，比太阳到比邻星还远。
它的内部正在诞生新的恒星，这是一个宇宙产房。
你现在看到的画面，是6500年前的它。
人类登上过月球，但这个地方，我们可能永远到不了。
所以我们把它画出来。
"""

IMAGES = [
    {"path": "F:/tmp/pillars_wide.png",           "text": "📍 距离地球6500光年"},
    {"path": "F:/tmp/pillars_of_creation.png",    "text": "韦伯红外影像 -> AI渲染可见光"},
    {"path": "F:/tmp/pillars_closeup.png",        "text": "里面正在诞生新的恒星"},
    {"path": "F:/tmp/pillars_of_creation.png",    "text": "这是6500年前的宇宙"},
]

TITLE_TEXT = "NASA看不到的颜色\n我画出来了"
OUTRO_TEXT = "下期想看哪个星云？\n评论区见"
OUTPUT = "F:/tmp/深空画布_创生之柱.mp4"
FPS = 24
W, H = 1080, 1920


def make_segment(img_path, duration, subtitle_text):
    """图片 + 底部字幕，带微弱缩放"""
    clip = ImageClip(img_path).resized((W, H))

    # 简单缩放：从 1.0x 到 1.06x（肉眼几乎看不出但避免完全静止）
    def zoom_effect(t):
        scale = 1.0 + 0.06 * (t / duration) if duration > 0 else 1.0
        return clip.resized((int(W * scale), int(H * scale))).cropped(
            x_center=W/2, y_center=H/2, width=W, height=H
        ).get_frame(t)

    from moviepy import VideoClip
    zoomed = VideoClip(zoom_effect, duration=duration)

    if subtitle_text:
        txt = TextClip(
            text=subtitle_text,
            font="C:/Windows/Fonts/msyh.ttc",
            font_size=44,
            color="white",
            stroke_color="black",
            stroke_width=2,
            method="caption",
            size=(W - 80, None)
        ).with_position(("center", H * 0.80)).with_duration(duration)
        return CompositeVideoClip([zoomed, txt]).with_duration(duration)

    return zoomed.with_duration(duration)


def make_card(img_path, text, duration, font_size=68):
    """标题/结束卡片"""
    bg = ImageClip(img_path).resized((W, H))
    txt = TextClip(
        text=text,
        font="C:/Windows/Fonts/msyhbd.ttc",
        font_size=font_size,
        color="white",
        stroke_color="black",
        stroke_width=4,
        method="caption",
        size=(W - 60, None),
        text_align="center"
    ).with_position("center").with_duration(duration)
    return CompositeVideoClip([bg, txt]).with_duration(duration)


async def main():
    print("==== 深空画布 视频合成 ====")
    print(f"分辨率: {W}x{H}")

    # 配音
    voice_path = "F:/tmp/voiceover.mp3"
    print(f"生成配音...")
    communicate = edge_tts.Communicate(VOICEOVER_TEXT.strip(), "zh-CN-XiaoxiaoNeural", rate="+8%")
    await communicate.save(voice_path)
    voice = AudioFileClip(voice_path)
    print(f"配音时长: {voice.duration:.1f}s")

    # 时间分配
    TITLE_DUR = 2.0
    OUTRO_DUR = 2.5
    body_dur = max(voice.duration - TITLE_DUR - OUTRO_DUR, len(IMAGES) * 2)
    per_img = body_dur / len(IMAGES)

    # 组装
    clips = [
        make_card("F:/tmp/pillars_of_creation.png", TITLE_TEXT, TITLE_DUR, 72),
    ]
    for i, img in enumerate(IMAGES):
        clips.append(make_segment(img["path"], per_img, img["text"]))
        print(f"  片段{i+1}: {img['path'].split('/')[-1]} ({per_img:.1f}s)")

    clips.append(make_card("F:/tmp/pillars_wide.png", OUTRO_TEXT, OUTRO_DUR, 56))

    video = concatenate_videoclips(clips, method="compose")
    print(f"视频总长: {video.duration:.1f}s")

    # 配音对齐
    if voice.duration > video.duration:
        voice = voice.subclipped(0, video.duration)
    video = video.with_audio(voice)

    # 导出
    print(f"渲染中...")
    video.write_videofile(
        OUTPUT, fps=FPS, codec="libx264",
        audio_codec="aac", preset="medium", bitrate="6000k"
    )
    print(f"\n==== 完成! ====")
    print(f"文件: {OUTPUT}")
    print(f"上传: 小红书App -> 发布 -> 视频 -> 勾选「含AI合成内容」")


if __name__ == "__main__":
    asyncio.run(main())
