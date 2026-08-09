---
name: gpt-image2-generator
description: 通过 OpenAI 兼容网关的 /v1/images/generations 接口生成 gpt-image-2 图片。当用户要求生成图片、画图、出图，或提到 gpt-image-2、images API 时使用。服务地址与密钥从环境变量或配置文件读取，绝不硬编码或明文输出。
---

# gpt-image-2 图片生成

## 用途

调用 OpenAI 兼容网关（如 sub2api 等自建网关）的 `/v1/images/generations` 接口，使用 gpt-image-2 模型生成图片。
适用于 Codex 等固定使用 `/v1/responses` 协议的客户端无法生图时，改用 images API 直连出图。

## 配置（安全要求）

配置二选一，**优先级：环境变量 > 配置文件**。

**方式 A：环境变量**

```
GPT_IMAGE_API_BASE_URL=https://你的网关地址
GPT_IMAGE_API_KEY=sk-xxxx
```

**方式 B：配置文件** `~/.gpt-image2/config.json`

```json
{
  "base_url": "https://你的网关地址",
  "api_key": "sk-xxxx"
}
```

> 安全铁律：任何情况下不得在代码、日志、回复中输出或硬编码 base_url 与 api_key 明文。若用户粘贴了密钥，先引导写入配置文件（权限设为仅本人可读）或环境变量，再使用。

## 使用

```bash
python scripts/generate_image.py --prompt "一只戴帽子的橘猫，油画风格"

python scripts/generate_image.py --prompt "赛博朋克城市夜景" --size 1024x1536 --output 城市.png

python scripts/generate_image.py --prompt "..." --quality high --n 2 --output 多张
```

参数说明：

| 参数 | 说明 |
|---|---|
| `--prompt` | 必填，图片描述 |
| `--model` | 默认 `gpt-image-2` |
| `--size` | 默认 `1024x1024`，可选 `1024x1536`、`1536x1024`、`auto`（以网关支持为准） |
| `--quality` | 可选，如 `low` / `medium` / `high`（透传） |
| `--n` | 可选，生成张数（透传，默认 1） |
| `--output` | 输出路径；多张时作为文件名前缀（如 `多张_1.png`） |

## 工作流

1. 确认配置存在（环境变量或配置文件）；缺失时引导用户配置，不代填密钥
2. 运行脚本生成图片
3. 校验输出文件存在且非空
4. 告知用户图片保存路径

## 常见错误对照

| 状态码 | 含义 | 处理 |
|---|---|---|
| 401 | API Key 无效 | 检查密钥是否正确 |
| 403 | 该 Key 所在分组未开启图片生成权限 | 在网关后台为分组开启图片权限 |
| 400 | 参数不被支持 | 检查 model / size 是否被网关支持 |
| 502 | 上游网关错误 | 网关不可达，或上游不支持该接口 |
| 网络错误 | 连接失败 | 检查网络能否到达网关地址 |

## 安装到 Codex（可选）

将本目录复制到 Codex 的 skills 目录即可被自动发现：

```bash
# 复制到用户级 skills 目录
mkdir -p ~/.codex/skills
cp -r gpt-image2-generator ~/.codex/skills/
```

## 脚本说明

`scripts/generate_image.py` 仅使用 Python 标准库（urllib / base64 / json），无需安装任何依赖。base_url 自动兼容三种写法：`https://host/`、`https://host/v1`、`https://host/v1/images/generations`。
