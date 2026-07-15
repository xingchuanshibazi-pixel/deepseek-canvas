"""
quality_check.py — AI 壁纸多维度质量验证
锐度 / 亮度 / 色彩 / 构图 → 综合打分 → PASS/FAIL/RETRY
"""
import sys, io, json, os
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ─── 阈值配置 ───
THRESHOLDS = {
    "sharpness_min": 200,     # 拉普拉斯方差（SDXL 20步通常 > 400）
    "brightness_min": 25,     # 不能全黑
    "brightness_max": 235,    # 不能全白
    "color_std_min": 20,      # RGB 标准差均值，太低=灰蒙蒙
    "dark_ratio_max": 0.70,   # 暗部像素比例上限
    "bright_ratio_max": 0.50, # 过曝像素比例上限（光照场景可达 25%+）
}

WEIGHTS = {
    "sharpness": 0.40,
    "brightness": 0.20,
    "color": 0.20,
    "composition": 0.20,
}


def compute_sharpness(img):
    gray = np.array(img.convert("L"), dtype=np.float64)
    lap = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
    edges = ndimage.convolve(gray, lap)
    return float(edges.var())


def compute_brightness(img):
    gray = np.array(img.convert("L"))
    return {
        "mean": float(gray.mean()),
        "dark_pct": float((gray < 30).sum() / gray.size),
        "bright_pct": float((gray > 240).sum() / gray.size),
    }


def compute_color(img):
    arr = np.array(img.convert("RGB"))
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    return float((r.std() + g.std() + b.std()) / 3)


def check_image(image_path):
    """单张图片质量检查"""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    size_kb = os.path.getsize(image_path) / 1024

    sharp = compute_sharpness(img)
    bright = compute_brightness(img)
    color = compute_color(img)
    img.close()

    results = {}
    # 锐度
    results["sharpness"] = {
        "value": round(sharp, 0),
        "pass": sharp >= THRESHOLDS["sharpness_min"],
        "threshold": THRESHOLDS["sharpness_min"],
    }
    # 亮度
    b_ok = (THRESHOLDS["brightness_min"] <= bright["mean"] <= THRESHOLDS["brightness_max"])
    results["brightness"] = {
        "value": f"mean={bright['mean']:.0f}",
        "pass": b_ok,
        "threshold": f"{THRESHOLDS['brightness_min']}-{THRESHOLDS['brightness_max']}",
    }
    # 色彩
    results["color"] = {
        "value": round(color, 0),
        "pass": color >= THRESHOLDS["color_std_min"],
        "threshold": THRESHOLDS["color_std_min"],
    }
    # 构图
    c_ok = (bright["dark_pct"] <= THRESHOLDS["dark_ratio_max"] and
            bright["bright_pct"] <= THRESHOLDS["bright_ratio_max"])
    results["composition"] = {
        "value": f"dark={bright['dark_pct']:.1%} bright={bright['bright_pct']:.1%}",
        "pass": c_ok,
        "threshold": f"dark<{THRESHOLDS['dark_ratio_max']:.0%} bright<{THRESHOLDS['bright_ratio_max']:.0%}",
    }

    # 综合分
    score = 0
    for dim, weight in WEIGHTS.items():
        if results[dim]["pass"]:
            score += weight * 100

    passed = all(r["pass"] for r in results.values())
    failures = [f"{dim}: {r['value']} (threshold {r['threshold']})"
                for dim, r in results.items() if not r["pass"]]

    return {
        "file": os.path.basename(image_path),
        "resolution": f"{w}x{h}",
        "size_kb": round(size_kb, 0),
        "passed": passed,
        "score": round(score, 0),
        "dimensions": results,
        "failures": failures,
    }


def check_directory(image_dir, glob_pattern="*.png"):
    """批量检查目录下所有图片"""
    files = sorted(Path(image_dir).glob(glob_pattern))
    if not files:
        print(f"未找到图片: {image_dir}/{glob_pattern}")
        return []

    reports = []
    for f in files:
        reports.append(check_image(str(f)))

    # 打印报告
    print(f"{'='*65}")
    print(f"质量检查: {image_dir}  ({len(files)} 张)")
    print(f"{'='*65}")
    passed = sum(1 for r in reports if r["passed"])
    for r in reports:
        status = "PASS" if r["passed"] else "FAIL"
        dims = r["dimensions"]
        print(f"\n{r['file']} [{status}]  score={r['score']:.0f}")
        print(f"  sharpness={dims['sharpness']['value']:.0f} "
              f"| brightness={dims['brightness']['value']} "
              f"| color={dims['color']['value']:.0f} "
              f"| comp={dims['composition']['value']}")
        if r["failures"]:
            for f in r["failures"]:
                print(f"  [FAIL] {f}")

    print(f"\n{'='*65}")
    print(f"结果: {passed}/{len(files)} PASS")
    if passed < len(files):
        failed = [r for r in reports if not r["passed"]]
        for r in failed:
            print(f"  [需重出] {r['file']}: {', '.join(r['failures'])}")

    return reports


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="AI 壁纸质量检查")
    p.add_argument("path", help="图片文件或目录")
    p.add_argument("--pattern", default="*.png", help="glob 模式 (默认: *.png)")
    p.add_argument("--json", action="store_true", help="JSON 输出")
    args = p.parse_args()

    path = Path(args.path)
    if path.is_file():
        report = check_image(str(path))
        reports = [report]
    else:
        reports = check_directory(str(path), args.pattern)

    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
