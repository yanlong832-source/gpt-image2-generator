#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 /v1/images/generations 生成 gpt-image-2 图片（仅 Python 标准库）

配置来源（优先级）：环境变量 GPT_IMAGE_API_BASE_URL / GPT_IMAGE_API_KEY
                        > 配置文件 ~/.gpt-image2/config.json
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

CONFIG_FILE = os.path.expanduser("~/.gpt-image2/config.json")


def load_config():
    """返回 (base_url, api_key)，未找到配置时退出"""
    base_url = os.environ.get("GPT_IMAGE_API_BASE_URL", "").strip()
    api_key = os.environ.get("GPT_IMAGE_API_KEY", "").strip()
    if not base_url or not api_key:
        cfg = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                print(f"警告：配置文件 {CONFIG_FILE} 解析失败，将忽略")
        if not base_url:
            base_url = str(cfg.get("base_url", "")).strip()
        if not api_key:
            api_key = str(cfg.get("api_key", "")).strip()
    if not base_url or not api_key:
        print("错误：未找到 API 配置。请二选一：")
        print("  1) 设置环境变量 GPT_IMAGE_API_BASE_URL 与 GPT_IMAGE_API_KEY")
        print(f"  2) 创建配置文件 {CONFIG_FILE}，内容：")
        print('     {"base_url": "https://你的网关地址", "api_key": "sk-xxxx"}')
        sys.exit(2)
    return base_url.rstrip("/"), api_key


def build_endpoint(base_url):
    """兼容 base_url 的三种写法"""
    if base_url.endswith("/images/generations"):
        return base_url
    if base_url.endswith("/v1"):
        return base_url + "/images/generations"
    return base_url + "/v1/images/generations"


def main():
    ap = argparse.ArgumentParser(description="通过 /v1/images/generations 生成 gpt-image-2 图片")
    ap.add_argument("--prompt", required=True, help="图片描述（必填）")
    ap.add_argument("--model", default="gpt-image-2", help="模型名，默认 gpt-image-2")
    ap.add_argument("--size", default="1024x1024", help="尺寸，默认 1024x1024")
    ap.add_argument("--output", default="", help="输出路径；多张时作为前缀")
    ap.add_argument("--quality", default=None, help="质量：low/medium/high（可选）")
    ap.add_argument("--n", type=int, default=None, help="生成张数（可选，默认 1）")
    args = ap.parse_args()

    base_url, api_key = load_config()
    endpoint = build_endpoint(base_url)

    payload = {"model": args.model, "prompt": args.prompt, "size": args.size,
               "n": args.n if args.n else 1}
    if args.quality:
        payload["quality"] = args.quality

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        hints = {
            401: "401：API Key 无效",
            403: "403：该 API Key 所在分组未开启图片生成权限",
            400: "400：请求参数不被支持（检查 model / size 等）",
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

    items = data.get("data") or []
    if not items:
        print("错误：响应中没有图片数据：" + json.dumps(data, ensure_ascii=False)[:500])
        sys.exit(1)

    output = args.output or f"gpt_image_{int(time.time())}"
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

    for p in saved:
        size = os.path.getsize(p) if os.path.exists(p) else 0
        if size == 0:
            print(f"警告：{p} 文件为空")
        else:
            print(f"已生成：{p}（{size} 字节）")


if __name__ == "__main__":
    main()
