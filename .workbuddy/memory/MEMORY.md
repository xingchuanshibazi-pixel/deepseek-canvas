# 深空画布 · 项目记忆

## 项目是什么

AI 科普短视频自动生产线。输入 AI 图片 + JSON 脚本 → 输出小红书竖屏 MP4（1080×1920）。

## 当前状态

- **版本**: v3.3（FFmpeg zoompan + BGM + 钩子 + CTA + 节奏 + 音效 + 色彩 + 分屏）
- **管线可运行**: ✅ pipeline/v3 路径已去硬编码；tools/ 需配置环境变量
- **依赖**: Python 3.10+, FFmpeg, edge_tts, moviepy, Pillow
- **网络要求**: edge_tts 需联网（国内需 HTTP_PROXY 代理）

## 关键文件

| 文件 | 用途 |
|------|------|
| `pipeline/video_pipeline_v3.py` | ★ 主力管线 v3.3，入口 |
| `scripts/*.json` | 视频脚本（4个：创生之柱/巨齿鲨/山海经/马里亚纳海沟） |
| `assets/ai/*.png` | 图片素材（32张：4选题 × 8张） |
| `tools/cover_maker.py` | 封面生成器 |
| `CLAUDE.md` | AI 工具通用说明书 |
| `GUIDE.md` | 人类教程 |
| `EVOLUTION.md` | 版本演进记录 |
| `README.md` | 入门指南 |

## 技术决策记录

1. **配音选 edge_tts 而非 API** — 免费，质量够用
2. **运镜用 FFmpeg 而非 MoviePy** — 平滑度差距明显
3. **去掉所有字幕** — 二次元画风需要沉浸感
4. **JSON 脚本分离** — 内容创作者不需要懂代码
5. **BGM/音效用 FFmpeg 合成** — 零外部音频依赖

## 📋 任务看板

> 开工前先读这个表，避免撞车。完成后更新状态。
> 状态：⬜ 待领 · 🟡 进行中 · ✅ 完成

| 任务 | 状态 | 谁在做 | 备注 |
|------|:--:|------|------|
| 马里亚纳海沟 出图+出片 | ✅ 完成 | WorkBuddy | 8张图+60MB视频已完成 |
| 管线 P0~P3 四级升级 | ✅ 完成 | Claude Code | v3.0→v3.3 |
| **用 v3.3 重跑巨齿鲨+创生之柱** | 🟡 **待 WorkBuddy 领** | — | 管线升级后需重出片 |
| 用 v3.3 生成封面（4个选题） | 🟡 待领 | — | `python tools/cover_maker.py scripts/xxx.json` |
| 太阳的声音 写脚本+出图 | ⬜ 待领 | — | 内容计划已有文案 |
| LLM 自动写 JSON 脚本（v4） | ⬜ 待领 | — | |

## 🤝 协作公约

所有 AI 助手（Claude Code、WorkBuddy 等）在本项目工作时的共同约定：

### 开工前
1. `git pull` 拉最新代码
2. 读本文件看板，确认任务没被其他人领走
3. 从 master 开新分支，不直接在 master 上改

### 干活时
4. 一个分支只做一个任务
5. 遇到不确定的事留注释 `TODO: 待确认`，不硬猜
6. 不跨任务改无关文件

### 收工时
7. 更新本文件看板状态
8. commit 格式：`[任务名] 做了什么`
9. `git push` 推到自己分支
10. 告诉人类"我干完了，可以合并"

## 2026-07-15 工作记录

### 第一轮（Claude Code）— 项目整理
把管线从工作目录（含 ~70 个无关文件）提取为独立项目包：
- 去硬编码 6 处、新建 3 份文档、创建 CLAUDE.md
- 24 张图片 + 示例视频；v1/v2 保留为学习参考

### 第二轮（WorkBuddy）— 独立审计
- 发现 `batch_gen_anime.py` 前缀错位（ameg→cmeg）
- 发现 `image_sourcer.py` 硬编码路径
- 发现 CLAUDE.md 描述不准确
- 以上均已修复

### 第三轮（Claude Code）— 管线四级升级 v3.0→v3.3
- **v3.1**: BGM 环境音（4种情绪，FFmpeg 合成）+ 开场大字钩子 + 结尾 CTA + 节奏控制 + 封面生成器
- **v3.2**: 多图交替切换 + 音效（ding/whoosh/boom/tick）
- **v3.3**: 色彩预设（warm/cool/vivid/film）+ 分屏对比（layout=compare）

### 第四轮（WorkBuddy）— 马里亚纳海沟完成
- 生成 mari_01~08.png 深海图片
- 出片 output/深空画布_马里亚纳海沟_v1.mp4

---

### ⚠️ 给 WorkBuddy 的下一条消息

> 管线已升级到 v3.3。巨齿鲨的脚本 `scripts/巨齿鲨_v3.json` 已经加了所有新字段作为演示（hook/BGM/CTA/pace/sfx）。
> 
> 请做：
> 1. `git pull` 拉最新代码
> 2. 用 v3.3 重跑巨齿鲨和创生之柱（让老选题用上新功能）
> 3. 用 `python tools/cover_maker.py scripts/xxx.json` 生成 4 个选题的封面
> 4. 完成后更新本看板
