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
    ("mari_01", "deep ocean descent from sunlit surface to absolute darkness, vertical depth gradient with sunlight fading into midnight zone, Japanese anime style, masterpiece, detailed, dramatic blue lighting, educational illustration"),
    ("mari_02", "Mariana Trench cross-section with Mount Everest upside down submerged and still short of surface, immense scale comparison, dark abyss, Japanese anime style, detailed, epic composition, blue-black depths"),
    ("mari_03", "solitary explorer at the deepest point of Earth contrasting with moon landing, tiny lonely figure in vast dark ocean trench, sense of isolation, Japanese anime style, atmospheric, mysterious"),
    ("mari_04", "ocean depth layers from sunlight zone to midnight zone to abyss to hadal zone, gradient shifting from bright blue to pitch black, Japanese anime style, clean educational illustration"),
    ("mari_05", "looking up from the trench bottom into absolute darkness, bioluminescent deep sea creatures glowing faintly, tiny points of light scattered in black water, Japanese anime style, beautiful, mysterious, ethereal"),
    ("mari_06", "deep sea snailfish at 8000m depth, translucent body, no scales, soft skeleton, glowing faintly under crushing pressure, Japanese anime style, detailed creature design, beautiful and melancholic"),
    ("mari_07", "Earth viewed from space with 71 percent covered by ocean, unexplored deep depths highlighted, contrast with Mars rover, Japanese anime style, cosmic perspective, glowing blue planet"),
    ("mari_08", "hydrothermal vent black smoker on seafloor, 370C mineral rich water erupting from cracks, bizarre creatures thriving without sunlight, Japanese anime style, dramatic, alien ecosystem, glowing"),
]

# ============================================================
# 执行（如果你的出图工具不是 Wallpaper Lab，改下面的命令）
# ============================================================
OUT.mkdir(parents=True, exist_ok=True)

for name, prompt in PROMPTS:
    path = OUT / f"{name}.png"
    cmd = f'cd "{WALLPAPER_LAB}" && "{sys.executable}" wallpaper.py sd -p "{prompt}" -s anime -r 1080p --orientation portrait --output "{path}"'
    print(f"生成 {name}...")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    if r.returncode == 0:
        print(f"  OK {name}.png")
    else:
        print(f"  FAIL {name}: {r.stderr[-100:]}")
        sys.exit(1)

print(f"\n==== 全部完成，输出到 {OUT} ====")
