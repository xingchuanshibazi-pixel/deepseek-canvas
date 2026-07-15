# 深空画布 · 完整教程

从零开始，做一个 AI 科普视频。

---

## 管线全景

整个管线分 **6 层**，每层解决一个问题：

```
选题 & 文案          ← 你要讲什么故事？
    ↓
JSON 脚本            ← 把故事拆成 6-8 个场景
    ↓
图片素材             ← 每个场景配一张图
    ↓
配音生成             ← edge_tts 把文字变成人声
    ↓
运镜 & 合成          ← FFmpeg zoompan 让静态图片动起来
    ↓
MP4 输出             ← 1080×1920 竖屏，直接发小红书
```

---

## 第一层：选题和文案

一个 2-3 分钟的科普视频，大概需要 **600-800 字旁白**，拆成 **6-8 个场景**。

每个场景做一件事：
- 场景 1：制造悬念/引入话题
- 场景 2-6：核心知识点（一个场景 = 一个点）
- 场景 7-8：收尾/升华

参考 `reference/小红书内容计划-第一周.md` 看看实际选题是怎么策划的。

---

## 第二层：写 JSON 脚本

这是整个流程最关键的环节。JSON 脚本定义了视频的全部内容。

### 最小示例

```json
{
  "title": "我的第一个视频",
  "voice": "zh-CN-YunxiNeural",
  "output": "我的视频.mp4",
  "scenes": [
    {
      "id": 1,
      "narration": "这是第一段旁白，会被读出来。",
      "rate": "+0%",
      "pitch": "+0Hz",
      "image_path": "assets/ai/my_image_01.png",
      "zoom": "in"
    }
  ]
}
```

### 字段说明

| 字段 | 必须？ | 说明 |
|------|:--:|------|
| `title` | ✅ | 视频标题（显示在终端日志里） |
| `voice` | ✅ | TTS 配音人。推荐 `zh-CN-YunxiNeural`（男声） |
| `output` | 否 | 输出文件名。不写则用 title |
| `scenes` | ✅ | 场景数组，6-8 个 |
| `scenes[].id` | ✅ | 场景编号，从 1 开始 |
| `scenes[].narration` | ✅ | 旁白文字，80-150 字最佳 |
| `scenes[].rate` | ✅ | 语速。`-10%`（慢/深沉）到 `+10%`（快/兴奋） |
| `scenes[].pitch` | ✅ | 音高。`-10Hz`（低沉）到 `+10Hz`（激昂） |
| `scenes[].image_path` | ✅ | 图片路径，基于项目根目录 |
| `scenes[].zoom` | 否 | 运镜方向，不写则自动轮换 |

### 运镜方向

| 值 | 效果 | 适合场景 |
|------|------|------|
| `in` | 逐渐推进 | 揭示真相、强调细节 |
| `out` | 逐渐拉远 | 展示宏大、结尾升华 |
| `left` | 向左平移 | 叙事过渡 |
| `right` | 向右平移 | 叙事过渡 |
| `up` | 向上平移 | 仰望感 |
| `down` | 向下平移 | 坠落感、深海 |

如果不写 `zoom`，管线会自动轮换 8 种方向 `["in", "right", "out", "left", "up", "in", "left", "out"]`，防止单调。

### 情感参数技巧

```
制造悬念 → rate: "-5%",  pitch: "+0Hz"   （慢一点，吊胃口）
揭示事实 → rate: "+3%",  pitch: "+3Hz"   （正常偏快）
震撼数据 → rate: "+5%",  pitch: "+8Hz"   （快+亢奋）
结尾升华 → rate: "-8%",  pitch: "-2Hz"   （慢+深沉）
```

---

## 第三层：准备图片

### 方法 1：自己用 AI 生成（推荐）

`tools/batch_gen_anime.py` 是一个批量生成示例，核心命令是：

```bash
# 需要 Wallpaper Lab 项目
cd F:/claude/wallpaper-lab
python wallpaper.py sd \
  -p "你的提示词" \
  -s anime \
  -r 1080p \
  --orientation portrait \
  --output assets/ai/my_image_01.png
```

### 方法 2：手动准备

把任意图片放到 `assets/ai/`，然后用 `tools/image_sourcer.py` 自动裁切成 1080×1920 竖屏：

```python
from image_sourcer import resize_to_portrait
resize_to_portrait("我的图片.jpg", "assets/ai/my_image_01.png")
```

### 方法 3：NASA 图片库

`image_sourcer.py` 内置了 NASA API 集成，可以搜索并下载真实天文照片。

### 图片规格

- 分辨率：1080 × 1920（9:16 竖屏）
- 格式：PNG（推荐）或 JPG
- 数量：6-8 张（一个场景一张）

---

## 第四层：配音

`video_pipeline_v3.py` 使用 Microsoft Edge TTS（免费），每场景独立生成 MP3。

**工作原理：**
1. 按场景旁白调用 edge_tts
2. 长文本自动拆句（按标点符号分割）
3. MD5 缓存：相同文本不重复请求
4. 失败自动重试 5 次

**配音人选择：**
| voice | 性别 | 风格 |
|-------|:--:|------|
| `zh-CN-YunxiNeural` | 男 | 活泼阳光（推荐） |
| `zh-CN-YunyangNeural` | 男 | 沉稳大气 |
| `zh-CN-XiaoxiaoNeural` | 女 | 温柔亲切 |
| `zh-CN-XiaoyiNeural` | 女 | 知性冷静 |

---

## 第五层：运镜和合成

### FFmpeg zoompan

v3 使用 FFmpeg 的 `zoompan` 滤镜实现平滑缩放和平移——这就是视频里画面"动起来"的效果。

整个过程完全在 CPU 上完成，不需要显卡。

### 合成流程

```
开场（第一张图 Fade In, 2秒）
    ↓
场景1（图片 + 配音 + zoompan）
    ↓  -0.5秒交叉过渡
场景2
    ↓
  ...
    ↓
场景N
    ↓
结尾（最后一张图 Fade Out, 3秒）
```

每个场景的过渡有 0.5 秒重叠（`padding=-0.5`），让切换更自然。

### 视频参数

- 分辨率：1080 × 1920
- 帧率：24 FPS
- 编码：H.264
- 码率：6000 kbps
- 音频：AAC

---

## 第六层：输出

视频输出到 `output/` 目录。可以直接上传到小红书、抖音、视频号等平台。

上传时注意勾选"含 AI 合成内容"。

---

## 完整流程速查

```bash
# 1. 安装
pip install -r requirements.txt

# 2. 准备图片（放到 assets/ai/）

# 3. 写脚本（参考 scripts/ 里的示例）

# 4. 生成视频
python pipeline/video_pipeline_v3.py scripts/你的脚本.json

# 5. 查看结果
# output/ 目录下的 MP4 文件
```

---

## 做一个新选题的 Checklist

- [ ] 确定选题（天文/深海/史前/神话？）
- [ ] 调研知识点，写 600-800 字文案
- [ ] 拆成 6-8 个场景，每个场景 80-150 字
- [ ] 确定每场景的情感基调（rate/pitch）
- [ ] 生成/准备 6-8 张 AI 图片
- [ ] 写 JSON 脚本
- [ ] 运行管线
- [ ] 检查输出视频，调整不满意的地方
- [ ] 发布
