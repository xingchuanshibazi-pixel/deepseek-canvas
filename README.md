# 深空画布 · Deep Space Canvas

> 把宇宙、深海、史前世界画给你看 🌌  
> AI 科普视频自动生产线 — 从一张图和一段文案到竖屏短视频

## 这是什么

这是一个 **AI 驱动的科普短视频生产线**。给定一组 AI 生成的图片和一段 JSON 脚本，它能自动完成配音、画面运镜、视频合成，输出小红书/抖音格式的竖屏视频（1080×1920）。

3 个已完成的示例选题：
- 🔭 创生之柱（天文）
- 🦈 巨齿鲨（史前巨兽）
- 📜 山海经异兽（神话传说）

## 效果预览

`examples/` 目录下有一个成品视频，可以先看看效果。

## 环境要求

| 工具 | 版本 | 怎么装 |
|------|------|--------|
| Python | 3.10 或更新 | [python.org](https://www.python.org/downloads/) |
| FFmpeg | 任意版本 | `winget install ffmpeg` 或 [ffmpeg.org](https://ffmpeg.org/download.html) |

## 三步跑起来

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. （国内用户）设置代理

edge_tts 需要访问微软服务器，国内网络可能需要代理：

```bash
# Windows PowerShell
$env:HTTP_PROXY="http://127.0.0.1:7890"

# Mac / Linux
export HTTP_PROXY=http://127.0.0.1:7890
```

如果你在国外或者网络能直连微软，跳过这一步。

### 3. 生成视频

```bash
python pipeline/video_pipeline_v3.py scripts/巨齿鲨_v3.json
```

等待几分钟（主要是配音生成耗时），视频会输出到 `output/` 目录。

## 目录结构

```
deepspace-canvas/
├── README.md              ← 你在这里
├── GUIDE.md               ← 详细教程：从头做一个选题
├── EVOLUTION.md           ← 管线演进史：v1→v2→v3
├── requirements.txt
│
├── pipeline/              ← 视频管线
│   ├── video_pipeline_v3.py   ★ 主力版本
│   ├── video_pipeline_v2.py   学习参考
│   └── create_video.py        最简原型
│
├── tools/                 ← 辅助工具
│   ├── image_sourcer.py
│   └── batch_gen_anime.py
│
├── scripts/               ← 视频脚本（JSON）
├── assets/ai/             ← AI 生成的图片素材
├── examples/              ← 示例输出视频
└── reference/             ← 参考资料
```

## 常见问题

### `❌ 找不到 ffmpeg！`

需要安装 FFmpeg 并加入系统 PATH：
- Windows: `winget install ffmpeg` 或去官网下载
- Mac: `brew install ffmpeg`
- Linux: `apt install ffmpeg`

### edge_tts 报错 / 配音失败

通常是网络问题。确认代理设置正确，或者多试几次（代码内置了 5 次重试）。

### 想自己做新选题

看 [GUIDE.md](GUIDE.md) — 从写脚本到出片的完整流程。

### 想了解代码是怎么演进的

看 [EVOLUTION.md](EVOLUTION.md) — 记录了从 130 行原型到完整管线的设计决策。
