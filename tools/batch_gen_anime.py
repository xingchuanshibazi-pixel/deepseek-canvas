"""批量生成二次元风格图片

⚠️ 这是一个可定制模板，不能直接运行：
1. 修改 PROMPTS 中的前缀和提示词，前缀需与 JSON 脚本的 image_path 一致
2. 设置 WALLPAPER_LAB 环境变量指向 Wallpaper Lab 项目路径（或改为你的 AI 出图工具）
3. 运行：python tools/batch_gen_anime.py

示例：将 PROMPTS 改为你的选题，前缀如 cmeg_（巨齿鲨）、cpil_（创生之柱）、shj_（山海经）等
"""
import subprocess, sys, os
from pathlib import Path

# 项目根
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
OUT = PROJECT_ROOT / "assets" / "ai"

# Wallpaper Lab 路径（通过环境变量配置）
WALLPAPER_LAB = Path(os.environ.get("WALLPAPER_LAB", "F:/claude/wallpaper-lab"))
if not WALLPAPER_LAB.exists():
    print(f"⚠️  Wallpaper Lab 未找到: {WALLPAPER_LAB}")
    print("   请设置环境变量 WALLPAPER_LAB 或修改此脚本")
    print("   如果你不用 Wallpaper Lab，请替换为你的 AI 出图命令")

# ============================================================
# 👇 修改这里：格式为 (文件名前缀, 英文提示词)
# ============================================================
PROMPTS = [
    ("cmeg_01", "megalodon giant ancient shark emerging from deep ocean abyss, epic scale, tiny human diver for size comparison, Japanese anime style, masterpiece, detailed, dramatic lighting, underwater scene"),
    ("cmeg_02", "megalodon size comparison with great white shark and human, three silhouettes side by side, accurate proportions, Japanese anime style, educational illustration, clean composition"),
    ("cmeg_03", "giant fossil shark tooth, 17cm, displayed in museum case, human hand next to it for scale, Japanese anime style, detailed, beautiful lighting"),
    ("cmeg_04", "megalodon open jaws, rows of sharp teeth, powerful bite force visualised, Japanese anime style, dramatic angle, dynamic composition, action scene"),
    ("cmeg_05", "megalodon hunting whale underwater, attacking from below, prehistoric ocean, Japanese anime style, epic battle scene, dynamic action"),
    ("cmeg_06", "lonely megalodon swimming in cold dark ocean, melancholic atmosphere, last of its kind, Japanese anime style, beautiful sad illustration, blue tones"),
    ("cmeg_07", "dark deep ocean abyss, mysterious giant shadow barely visible, myth vs reality, Japanese anime style, atmospheric, mysterious composition"),
    ("cmeg_08", "megalodon fossil teeth scattered on ancient ocean floor, sun rays from surface, beautiful memorial, Japanese anime style, poetic, nostalgic, masterpiece"),
]

# ============================================================
# 执行（如果你的出图工具不是 Wallpaper Lab，改下面的命令）
# ============================================================
OUT.mkdir(parents=True, exist_ok=True)

for name, prompt in PROMPTS:
    path = OUT / f"{name}.png"
    cmd = f'cd "{WALLPAPER_LAB}" && python wallpaper.py sd -p "{prompt}" -s anime -r 1080p --orientation portrait --output "{path}"'
    print(f"生成 {name}...")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    if r.returncode == 0:
        print(f"  OK {name}.png")
    else:
        print(f"  FAIL {name}: {r.stderr[-100:]}")
        sys.exit(1)

print(f"\n==== 全部完成，输出到 {OUT} ====")
