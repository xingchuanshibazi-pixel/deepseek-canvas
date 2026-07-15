# 深空画布 (Deep Space Canvas)

AI 驱动的科普短视频生产线。给定 AI 图片和 JSON 脚本，自动完成配音、运镜、合成，输出 1080×1920 竖屏 MP4。

## 项目结构

```
deepseek-canvas/
├── pipeline/                  ← 视频管线代码
│   ├── video_pipeline_v3.py   ★ 主力版本（可运行，路径已去硬编码）
│   ├── video_pipeline_v2.py   学习参考：展示 JSON 脚本分离、情感 TTS（勿直接运行）
│   └── create_video.py        最简原型：~130行硬编码，最适合初学者
├── tools/                     ← 辅助脚本
│   ├── image_sourcer.py       多源素材管道（本地/AI/NASA/CDP）
│   └── batch_gen_anime.py     批量 AI 出图（依赖 Wallpaper Lab）
├── scripts/                   ← 视频脚本（JSON）
├── assets/ai/                 ← 图片素材（1080×1920 PNG）
├── examples/                  ← 示例输出视频
├── reference/                 ← 内容策划文档
├── GUIDE.md                   ← 详细教程
├── EVOLUTION.md               ← v1→v2→v3 演进史
└── README.md                  ← 入门指南
```

## 架构分层（6 层）

```
选题 & 文案 → JSON 脚本 → 图片素材 → 配音(TTS) → 运镜(FFmpeg) → 合成(MoviePy) → MP4
```

## 核心入口

```bash
# 生成视频
python pipeline/video_pipeline_v3.py scripts/<脚本名>.json

# 依赖安装
pip install -r requirements.txt

# 需要 FFmpeg 在 PATH 中，edge_tts 需要网络（国内需代理）
```

## 技术栈

- **配音**: Microsoft Edge TTS (`edge_tts`)，每场景独立生成，MD5 缓存，5 次重试
- **运镜**: FFmpeg `zoompan` 滤镜 — 6 种方向 (in/out/left/right/up/down)，逐场景自动轮换
- **合成**: MoviePy — 交叉过渡 padding=-0.5s，H.264 6000kbps
- **图片**: Pillow 预处理，1080×1920 竖屏裁切

## JSON 脚本格式

```json
{
  "title": "视频标题",
  "voice": "zh-CN-YunxiNeural",
  "output": "输出文件名.mp4",
  "hook": "开场钩子大字（可选，显示3秒）",
  "bgm": "auto 或 assets/bgm/xxx.mp3（可选，auto=自动生成环境音）",
  "bgm_mood": "neutral|deep|uplift|mystery（bgm=auto时生效）",
  "bgm_volume": 0.15,
  "scenes": [
    {
      "id": 1,
      "narration": "旁白文字（80-150字）",
      "rate": "+0%",      // 语速: -10%(慢) ~ +10%(快)
      "pitch": "+0Hz",    // 音高: -10Hz(低沉) ~ +10Hz(激昂)
      "image_path": "assets/ai/xxx.png",  // 相对项目根
      "zoom": "in"        // in|out|left|right|up|down，可选（自动轮换）
    }
  ]
}
```

### 新增字段（v3.1）

| 字段 | 说明 |
|------|------|
| `hook` | 开场 3 秒大字钩子，吸引注意力。如 "比公交车还长的鲨鱼\n真的存在过" |
| `bgm` | 背景音乐路径，或 `"auto"` 自动生成环境音 |
| `bgm_mood` | BGM 情绪：`neutral`(通用) / `deep`(深海/深沉) / `uplift`(向上/希望) / `mystery`(神秘) |
| `bgm_volume` | BGM 音量，0=静音 1=原声。建议 0.10~0.20 |

## 运镜方向

| 值 | 效果 | 适合 |
|----|------|------|
| `in` | 逐渐推进 | 揭示真相、强调细节 |
| `out` | 逐渐拉远 | 宏大展示、结尾升华 |
| `left`/`right` | 平移 | 叙事过渡 |
| `up` | 上移 | 仰望感 |
| `down` | 下移 | 坠入/深海 |

## 路径约定

- `PROJECT_ROOT` = `Path(__file__).parent.parent`（即仓库根）
- `pipeline/video_pipeline_v3.py`：完全可移植，无硬编码路径
- `tools/` 下的脚本：通过环境变量配置外部依赖（`WALLPAPER_LAB`、`HTTP_PROXY`），不写死路径
- 脚本 `image_path` 可以是相对路径（自动拼项目根）或绝对路径
- 输出到 `output/`，临时文件用系统 temp 目录
- 代理从环境变量 `HTTP_PROXY` 读取

## 已知限制

- `tools/batch_gen_anime.py` 是模板，需按选题修改 PROMPTS 前缀和出图命令
- `tools/image_sourcer.py` 的 AI 生成功能依赖 Wallpaper Lab（通过 `WALLPAPER_LAB` 环境变量配置）
- 没有自动化测试——管线正确性靠人工看片验证
- 仅支持竖屏 9:16，无 BGM
- 图片需提前生成（管线本身不做 AI 出图）

## 代码规范

- Python 3.10+，UTF-8 编码
- 中文注释和日志输出
- 异步 I/O（asyncio）用于配音生成
- 子进程调用 FFmpeg（非 GPU，纯 CPU）
- 管线代码无文字叠加，无字体依赖

## 常见修改任务

### 新增选题
1. 准备 6-8 张 AI 图片到 `assets/ai/`
2. 写 JSON 脚本到 `scripts/`
3. 运行 `python pipeline/video_pipeline_v3.py scripts/xxx.json`

### 换配音人
修改脚本 `voice` 字段：
- `zh-CN-YunxiNeural`（男·活泼）
- `zh-CN-YunyangNeural`（男·沉稳）
- `zh-CN-XiaoxiaoNeural`（女·温柔）

### 调视频质量
修改 `video_pipeline_v3.py` 的 `W, H`（分辨率）、`FPS`（帧率）、`bitrate`（码率）

## 不要做的事

- 不要直接运行 v2 和 create_video.py（含硬编码路径，仅作学习参考）
- 不要改 `assets/ai/` 里被脚本引用的图片文件名（改了 JSON 也得同步改）
- 不要在 JSON 里用中文文件名（FFmpeg 可能不兼容）

## 协作规范

本项目可能由多个 AI 助手协作（Claude Code、WorkBuddy 等），通过 Gitee Git 仓库同步工作。
协作详情见 `.workbuddy/memory/MEMORY.md`（任务看板 + 公约）。

### 提交信息格式

```
[任务名] 做了什么

示例：
[马里亚纳海沟] 新增 8 张深海图片
[修复] batch_gen_anime.py 前缀错位
[文档] MEMORY.md 更新任务状态
```

### 工作流程

```
git pull → 读 MEMORY.md 看板 → 领任务 → 开分支 → 干活 → commit → push → 更新看板状态
```

### Git 工作分支

- `master` — 稳定版本，不直接改
- `feature/<任务名>` — 各任务独立分支
- 完成任务后在 MEMORY.md 看板更新状态，由人类审核合并
