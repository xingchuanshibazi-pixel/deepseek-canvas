"""批量生成二次元风格史前巨兽图片"""
import subprocess, sys

PROMPTS = [
    ("ameg_01", "megalodon giant ancient shark emerging from deep ocean abyss, epic scale, tiny human diver for size comparison, Japanese anime style, masterpiece, detailed, dramatic lighting, underwater scene"),
    ("ameg_02", "megalodon size comparison with great white shark and human, three silhouettes side by side, accurate proportions, Japanese anime style, educational illustration, clean composition"),
    ("ameg_03", "giant fossil shark tooth, 17cm, displayed in museum case, human hand next to it for scale, Japanese anime style, detailed, beautiful lighting"),
    ("ameg_04", "megalodon open jaws, rows of sharp teeth, powerful bite force visualised, Japanese anime style, dramatic angle, dynamic composition, action scene"),
    ("ameg_05", "megalodon hunting whale underwater, attacking from below, prehistoric ocean, Japanese anime style, epic battle scene, dynamic action"),
    ("ameg_06", "lonely megalodon swimming in cold dark ocean, melancholic atmosphere, last of its kind, Japanese anime style, beautiful sad illustration, blue tones"),
    ("ameg_07", "dark deep ocean abyss, mysterious giant shadow barely visible, myth vs reality, Japanese anime style, atmospheric, mysterious composition"),
    ("ameg_08", "megalodon fossil teeth scattered on ancient ocean floor, sun rays from surface, beautiful memorial, Japanese anime style, poetic, nostalgic, masterpiece"),
]

OUT = "F:/claude/deepseek/1/assets/ai"

for name, prompt in PROMPTS:
    path = f"{OUT}/{name}.png"
    cmd = f'cd F:/claude/wallpaper-lab && python wallpaper.py sd -p "{prompt}" -s anime -r 1080p --orientation portrait --output {path}'
    print(f"生成 {name}...")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    if r.returncode == 0:
        print(f"  ✅ {name}.png")
    else:
        print(f"  ❌ {name}: {r.stderr[-100:]}")
        sys.exit(1)

print("\n==== 全部完成 ====")
