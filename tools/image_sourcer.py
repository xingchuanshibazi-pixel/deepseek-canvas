"""
image_sourcer.py — 科普视频素材管道
支持三种来源：本地图片 / CDP 浏览器下载 / AI 生成补充
"""
import os
import sys
import shutil
import requests
from pathlib import Path
from PIL import Image

BASE_DIR = Path("F:/claude/deepseek/1/assets")
W, H = 1080, 1920  # 小红书/抖音竖屏
PROXY = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

# 全局 session 走代理
_session = requests.Session()
_session.proxies.update(PROXY)
_session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DeepSpaceCanvas/1.0"})


# ============================================================
# 图片预处理
# ============================================================

def resize_to_portrait(image_path, output_path, target_w=W, target_h=H):
    """将任意尺寸图片缩放裁切为竖屏 1080×1920"""
    img = Image.open(image_path)
    iw, ih = img.size

    # 先缩放到宽度=1080
    ratio = target_w / iw
    new_h = int(ih * ratio)
    img = img.resize((target_w, new_h), Image.LANCZOS)

    # 如果高度不够，缩放高度=1920 再裁宽度
    if new_h < target_h:
        ratio = target_h / ih
        new_w = int(iw * ratio)
        img = img.resize((new_w, target_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        img = img.crop((left, 0, left + target_w, target_h))
    else:
        # 高度多了，裁上下
        top = (new_h - target_h) // 2
        img = img.crop((0, top, target_w, top + target_h))

    img.save(output_path)
    return output_path


# ============================================================
# 来源1：本地图片
# ============================================================

def local_image(path):
    """使用本地已有图片"""
    if not os.path.exists(path):
        return None
    return path


# ============================================================
# 来源2：AI 生成（Wallpaper Lab / ComfyUI）
# ============================================================

def generate_ai(prompt, style="concept", output_name=None, portrait=True):
    """用 Wallpaper Lab sd 模式生成 AI 图片"""
    import subprocess

    if output_name is None:
        import hashlib
        output_name = f"ai_{hashlib.md5(prompt.encode()).hexdigest()[:8]}.png"

    output_path = BASE_DIR / "ai" / output_name
    ori = "--orientation portrait" if portrait else ""

    cmd = (
        f'cd F:/claude/wallpaper-lab && '
        f'python wallpaper.py sd '
        f'-p "{prompt}" -s {style} -r 1080p {ori} '
        f'--output {output_path}'
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    if result.returncode == 0 and output_path.exists():
        return str(output_path)
    print(f"  AI生成失败: {result.stderr[-200:] if result.stderr else 'unknown'}")
    return None


# ============================================================
# 来源3：NASA API（需代理）
# ============================================================

NASA_BASE = "https://images-api.nasa.gov"

def search_nasa(query, page=1):
    """搜索 NASA 图片库，返回 [{nasa_id, title, thumb_url}]"""
    try:
        resp = _session.get(
            f"{NASA_BASE}/search",
            params={"q": query, "media_type": "image", "page": page},
            timeout=15
        )
        if resp.status_code != 200:
            return []

        items = resp.json()["collection"]["items"]
        return [
            {
                "nasa_id": item["data"][0]["nasa_id"],
                "title": item["data"][0]["title"],
                "thumb_url": item.get("links", [{}])[0].get("href", ""),
            }
            for item in items if item.get("data")
        ]
    except Exception as e:
        print(f"  NASA搜索异常: {e}")
        return []


def download_nasa(nasa_id, output_dir=None):
    """下载 NASA 图片的最大分辨率版本"""
    if output_dir is None:
        output_dir = BASE_DIR / "nasa"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 获取所有文件URL
        resp = _session.get(f"{NASA_BASE}/asset/{nasa_id}", timeout=15)
        items = resp.json()["collection"]["items"]

        # 找最大图片（通常 .jpg 或 .png）
        image_urls = [i["href"] for i in items if i["href"].endswith((".jpg", ".jpeg", ".png", ".tif"))]

        if not image_urls:
            return None

        # 下载最大的一张
        url = image_urls[-1]
        fname = f"{nasa_id}{Path(url).suffix}"
        fpath = output_dir / fname

        img_resp = requests.get(url, timeout=30)
        with open(fpath, "wb") as f:
            f.write(img_resp.content)

        # 转换为竖屏
        portrait_path = output_dir / f"{nasa_id}_portrait.png"
        resize_to_portrait(fpath, portrait_path)
        return str(portrait_path)

    except Exception as e:
        print(f"  NASA下载异常 [{nasa_id}]: {e}")
        return None


# ============================================================
# 来源4：CDP 浏览器下载（兜底方案，用于反爬站点）
# ============================================================

def download_via_cdp(url, output_name, target=None):
    """通过 CDP 浏览器下载图片（利用用户浏览器的网络环境）"""
    import subprocess

    target = target or "F:/tmp/cdp_images"
    os.makedirs(target, exist_ok=True)
    fpath = f"{target}/{output_name}"

    # 用 CDP 浏览器下载: navigate -> eval 提取 blob -> 保存
    # 或者直接用 curl 带浏览器 cookies
    curl_cmd = f'curl -s -o "{fpath}" "{url}"'
    result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True, timeout=30)

    if result.returncode == 0 and os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
        return fpath
    return None


# ============================================================
# 统一接口：根据场景配置获取图片
# ============================================================

def fetch_image(scene):
    """
    根据场景配置智能获取图片。
    scene = {
        "image_source": "nasa"|"ai"|"local"|"cdp",
        "image_query": "...",
        "image_path": "..." (local模式),
        "image_fallback_ai": "..." (网络获取失败时的AI兜底prompt),
    }
    返回本地图片路径或 None
    """
    source = scene.get("image_source", "ai")
    query = scene.get("image_query", "")
    local_path = scene.get("image_path", "")
    fallback = scene.get("image_fallback_ai", "")

    # 1. 本地
    if source == "local" and local_path:
        path = local_image(local_path)
        if path:
            print(f"  [本地] {path}")
            return path

    # 2. NASA API
    if source == "nasa" and query:
        results = search_nasa(query)
        if results:
            print(f"  [NASA] 搜索 '{query}' → {len(results)} 结果")
            path = download_nasa(results[0]["nasa_id"])
            if path:
                print(f"  [NASA] 已下载: {path}")
                return path

    # 3. AI 生成（主要来源 + 网络失败时的兜底）
    if source == "ai" or (fallback and not os.path.exists(local_path or "")):
        prompt = query or fallback or source
        if prompt:
            print(f"  [AI] 生成中...")
            path = generate_ai(prompt)
            if path:
                print(f"  [AI] 已生成: {path}")
                return path

    # 4. 最终兜底
    print(f"  ⚠️  素材获取失败 [{source}]: {query}")
    return None


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    if "--test" in sys.argv:
        print("=== 素材管道测试 ===\n")

        # 测试 AI 生成
        print("1. AI 生成测试:")
        path = generate_ai(
            "Pillars of Creation, Eagle Nebula in visible light, realistic astrophotography, 8K",
            output_name="test_ai.png"
        )
        print(f"   结果: {path}\n")

        # 测试 NASA（可能因网络失败）
        print("2. NASA API 测试:")
        results = search_nasa("pillars of creation")
        print(f"   搜索结果: {len(results)} 条")
        if results:
            path = download_nasa(results[0]["nasa_id"])
            print(f"   下载: {path if path else '失败'}")
        print()

        print("=== 测试完成 ===")
