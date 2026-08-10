#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 OpenAI 兼容网关生成 / 编辑 gpt-image-2 图片（仅 Python 标准库）

支持三个功能：
1. 生成图片   --prompt "描述" [--n 4] [--composite]
2. 编辑图片   --edit 图片路径/URL --prompt "编辑要求" [--mask 蒙版]
3. 多图拼合   --n 4 --composite（生成后拼成网格）

配置来源（优先级）：环境变量 GPT_IMAGE_API_BASE_URL / GPT_IMAGE_API_KEY
                        > 配置文件 ~/.gpt-image2/config.json
"""
import argparse
import base64
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

CONFIG_FILE = os.path.expanduser("~/.gpt-image2/config.json")
CONFIG_TEMPLATE = {"base_url": "", "api_key": ""}

try:
    from PIL import Image  # 仅 --composite 需要（pip install pillow）
except ImportError:
    Image = None


def load_config():
    """返回 (base_url, api_key)，未找到配置时退出"""
    base_url = os.environ.get("GPT_IMAGE_API_BASE_URL", "").strip()
    api_key = os.environ.get("GPT_IMAGE_API_KEY", "").strip()
    config_created = False
    if not base_url or not api_key:
        cfg = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                print(f"警告：配置文件 {CONFIG_FILE} 解析失败，将忽略")
        else:
            config_dir = os.path.dirname(CONFIG_FILE)
            try:
                if config_dir:
                    os.makedirs(config_dir, exist_ok=True)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(CONFIG_TEMPLATE, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                try:
                    os.chmod(CONFIG_FILE, 0o600)
                except OSError:
                    pass
                config_created = True
            except OSError as error:
                print(f"警告：无法创建配置模板 {CONFIG_FILE}（{error}）")
        if not base_url:
            base_url = str(cfg.get("base_url", "")).strip()
        if not api_key:
            api_key = str(cfg.get("api_key", "")).strip()
    if not base_url or not api_key:
        if config_created:
            print(f"首次使用：已创建配置模板 {CONFIG_FILE}")
            print('请填入 "base_url" 和 "api_key" 后重新运行。')
        print("错误：未找到完整 API 配置。请二选一：")
        print("  1) 设置环境变量 GPT_IMAGE_API_BASE_URL 与 GPT_IMAGE_API_KEY")
        print(f"  2) 填写配置文件 {CONFIG_FILE}，内容：")
        print('     {"base_url": "https://你的网关地址", "api_key": "sk-xxxx"}')
        sys.exit(2)
    return base_url.rstrip("/"), api_key


def build_endpoint(base_url, kind):
    """kind: 'generations' 或 'edits'；兼容 base_url 三种写法"""
    for suffix in (f"/v1/images/{kind}", f"/images/{kind}"):
        if base_url.endswith(suffix):
            return base_url
    return base_url + f"/v1/images/{kind}"


def make_data_url(path):
    """本地图片文件 -> data URL；路径不存在或已是 URL 时原样返回"""
    if not os.path.exists(path):
        return path  # 视为 URL
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp", ".gif": "image/gif"}.get(
        os.path.splitext(path)[1].lower(), "image/png")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"


def api_post(endpoint, payload, api_key, base_url):
    """POST JSON 并返回响应 dict；失败时打印中文提示并退出"""
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        hints = {
            401: "401：API Key 无效",
            403: "403：该 API Key 所在分组未开启图片生成/编辑权限",
            400: "400：请求参数不被支持（检查 model / size / 图片格式等）",
            404: "404：模型或接口不被网关支持",
            429: "429：请求过于频繁，稍后重试",
            502: "502：上游网关错误（网关不可达或上游不支持该接口）",
            503: "503：上游服务暂时不可用",
        }
        print("错误：" + hints.get(e.code, f"HTTP {e.code}"))
        if body:
            print("响应内容：" + body[:500])
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"网络错误：无法连接 {base_url}（{e.reason}），请检查网络与地址")
        sys.exit(1)
    except Exception as e:
        print(f"错误：{e}")
        sys.exit(1)


def save_images(items, output):
    """保存图片数据（b64_json 或 url），返回保存路径列表"""
    output = output or f"gpt_image_{int(time.time())}"
    output_stem, output_extension = os.path.splitext(output)
    if output_extension.lower() == ".png":
        output = output_stem
    multi = len(items) > 1
    saved = []
    for i, item in enumerate(items):
        path = f"{output}_{i + 1}.png" if multi else f"{output}.png"
        if item.get("b64_json"):
            with open(path, "wb") as f:
                f.write(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            urllib.request.urlretrieve(item["url"], path)
        else:
            print(f"错误：第 {i + 1} 张图既无 b64_json 也无 url：" +
                  json.dumps(item, ensure_ascii=False)[:300])
            sys.exit(1)
        saved.append(path)
    return saved


def preview_markdown(paths):
    """返回可在支持 Markdown 的客户端中显示的本地预览链接。"""
    previews = []
    for index, path in enumerate(paths, start=1):
        absolute_path = os.path.abspath(path).replace(os.sep, "/")
        previews.append(f"![生成图片 {index}]({absolute_path})")
    return "\n".join(previews)


def composite_images(paths, output):
    """把多张图拼成网格（尽量接近正方形），输出 <output>_grid.png"""
    if Image is None:
        print("拼合功能需要 Pillow，请先安装：pip install pillow")
        sys.exit(1)
    if len(paths) < 2:
        print("拼合至少需要 2 张图")
        sys.exit(1)
    imgs = []
    for p in paths:
        try:
            imgs.append(Image.open(p).convert("RGB"))
        except Exception as e:
            print(f"无法打开图片 {p}：{e}")
            sys.exit(1)
    # 统一尺寸（以第一张为准）
    w, h = imgs[0].size
    imgs = [im.resize((w, h)) if im.size != (w, h) else im for im in imgs]
    n = len(imgs)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    canvas = Image.new("RGB", (w * cols, h * rows), (255, 255, 255))
    for i, im in enumerate(imgs):
        canvas.paste(im, ((i % cols) * w, (i // cols) * h))
    out = f"{output}_grid.png"
    canvas.save(out)
    return out


def main():
    ap = argparse.ArgumentParser(
        description="通过 /v1/images/generations 或 /v1/images/edits 生成/编辑 gpt-image-2 图片")
    ap.add_argument("--prompt", required=True, help="图片描述 / 编辑要求（必填）")
    ap.add_argument("--model", default="gpt-image-2", help="模型名，默认 gpt-image-2")
    ap.add_argument("--size", default="1024x1024", help="尺寸，默认 1024x1024")
    ap.add_argument("--output", default="", help="输出路径；多张时作为前缀")
    ap.add_argument("--quality", default=None, help="质量：low/medium/high（可选）")
    ap.add_argument("--n", type=int, default=None, help="生成张数（可选，默认 1）")
    ap.add_argument("--edit", default=None,
                    help="编辑模式：本地图片路径（自动转 data URL）或图片 URL")
    ap.add_argument("--mask", default=None,
                    help="编辑蒙版：本地图片路径或图片 URL（配合 --edit，可选）")
    ap.add_argument("--composite", action="store_true",
                    help="把本次生成的多个结果拼成一张网格图（需 pip install pillow）")
    ap.add_argument("--preview", action="store_true",
                    help="输出每张图片的 Markdown 本地预览链接")
    args = ap.parse_args()

    base_url, api_key = load_config()

    if args.edit:
        # ---- 图片编辑模式：POST /v1/images/edits ----
        endpoint = build_endpoint(base_url, "edits")
        images = [{"image_url": make_data_url(args.edit)}]
        if args.mask:
            images[0]["mask_url"] = make_data_url(args.mask)
        payload = {"model": args.model, "prompt": args.prompt, "images": images,
                   "n": args.n if args.n else 1}
        if args.size:
            payload["size"] = args.size
        data = api_post(endpoint, payload, api_key, base_url)
    else:
        # ---- 图片生成模式：POST /v1/images/generations ----
        endpoint = build_endpoint(base_url, "generations")
        payload = {"model": args.model, "prompt": args.prompt, "size": args.size,
                   "n": args.n if args.n else 1}
        if args.quality:
            payload["quality"] = args.quality
        data = api_post(endpoint, payload, api_key, base_url)

    items = data.get("data") or []
    if not items:
        print("错误：响应中没有图片数据：" + json.dumps(data, ensure_ascii=False)[:500])
        sys.exit(1)

    saved = save_images(items, args.output)

    if args.composite and len(saved) > 1:
        grid = composite_images(saved, args.output or f"gpt_image_{int(time.time())}")
        saved.append(grid)

    for p in saved:
        size = os.path.getsize(p) if os.path.exists(p) else 0
        if size == 0:
            print(f"警告：{p} 文件为空")
        else:
            print(f"已生成：{p}（{size} 字节）")
    if args.preview:
        print("预览（支持 Markdown 的客户端可直接显示）：")
        print(preview_markdown(saved))


if __name__ == "__main__":
    main()
