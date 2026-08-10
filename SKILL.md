---
name: gpt-image2-generator
description: 通过 OpenAI 兼容网关的 /v1/images/generations 与 /v1/images/edits 接口生成、编辑 gpt-image-2 图片，并支持多图拼合。当用户要求生成图片、画图、出图、编辑图片，或提到 gpt-image-2、images API 时使用。服务地址与密钥从环境变量或配置文件读取，绝不硬编码或明文输出。
---

# gpt-image-2 图片生成与编辑

## 用途

调用 OpenAI 兼容网关（如 sub2api 等自建网关）的 `/v1/images/generations`（生成）与 `/v1/images/edits`（编辑）接口，使用 gpt-image-2 模型处理图片。
适用于 Codex 等固定使用 `/v1/responses` 协议的客户端无法生图时，改用 images API 直连出图。

## 配置（安全要求）

配置二选一，**优先级：环境变量 > 配置文件**。

**方式 A：环境变量**

```
GPT_IMAGE_API_BASE_URL=https://你的网关地址
GPT_IMAGE_API_KEY=sk-xxxx
```

**方式 B：自动配置文件** `~/.gpt-image2/config.json`

```json
{
  "base_url": "https://你的网关地址",
  "api_key": "sk-xxxx"
}
```

首次运行时，若环境变量和配置都不完整，脚本会自动创建空模板 `~/.gpt-image2/config.json` 并显示实际路径。提示用户只在该文件中填入 `base_url` 和 `api_key` 后重试；不要由 Codex 代填或在回复中复述密钥。

> 安全铁律：任何情况下不得在代码、日志、回复中输出或硬编码 base_url 与 api_key 明文。若用户粘贴了密钥，先引导写入配置文件（权限设为仅本人可读）或环境变量，再使用。

## 使用

### 1. 生成图片

```bash
python scripts/generate_image.py --prompt "一只戴帽子的橘猫，油画风格" --preview

python scripts/generate_image.py --prompt "赛博朋克城市夜景" --size 1024x1536 --output 城市.png --preview
```

### 2. 编辑图片（/v1/images/edits）

```bash
# 编辑本地图片（自动转为 data URL 上传）
python scripts/generate_image.py --edit 原图.png --prompt "把天空改成黄昏色" --output 编辑后.png

# 编辑网络图片（直接传 URL）
python scripts/generate_image.py --edit https://example.com/photo.jpg --prompt "加上一只猫"

# 带蒙版编辑（只修改蒙版区域）
python scripts/generate_image.py --edit 原图.png --mask 蒙版.png --prompt "只把背景换成海滩"
```

### 3. 多图拼合（网格）

```bash
# 生成 4 张后自动拼成 2x2 网格（需要 pip install pillow）
python scripts/generate_image.py --prompt "同一只猫的四个表情" --n 4 --composite --output 表情包
```

## 参数说明

| 参数 | 说明 |
|---|---|
| `--prompt` | 必填，图片描述或编辑要求 |
| `--model` | 默认 `gpt-image-2` |
| `--size` | 默认 `1024x1024`，可选 `1024x1536`、`1536x1024`、`auto`（以网关支持为准） |
| `--quality` | 可选，如 `low` / `medium` / `high`（仅生成模式，透传） |
| `--n` | 可选，生成张数（默认 1） |
| `--output` | 输出路径；多张时作为文件名前缀（如 `多张_1.png`）；传入 `.png` 不会重复追加扩展名 |
| `--edit` | 进入编辑模式；值为本地图片路径或图片 URL |
| `--mask` | 编辑蒙版：本地路径或 URL（配合 `--edit`，可选） |
| `--composite` | 生成多张后拼成一张网格图（需 `pip install pillow`） |
| `--preview` | 输出每张结果的绝对路径 Markdown 预览链接 |

## 工作流

1. 带 `--preview` 运行脚本；缺失配置时，告知用户脚本已经创建的 `~/.gpt-image2/config.json` 路径，并提醒填写 `base_url` 与 `api_key`，不代填密钥
2. 按需求选择生成 / 编辑模式运行脚本
3. 校验输出文件存在且非空
4. 使用可用的本地图片预览工具检查结果，并在回复中以绝对路径 Markdown 图片链接展示预览；不要只给出文件路径

## 常见错误对照

| 状态码 | 含义 | 处理 |
|---|---|---|
| 401 | API Key 无效 | 检查密钥是否正确 |
| 403 | 该 Key 所在分组未开启图片生成/编辑权限 | 在网关后台为分组开启图片权限 |
| 400 | 参数不被支持 | 检查 model / size / 图片格式等 |
| 502 | 上游网关错误 | 网关不可达，或上游不支持该接口（如上游仅支持 curl 类客户端） |
| 网络错误 | 连接失败 | 检查网络能否到达网关地址 |

## 安装到 Codex（可选）

将本目录复制到 Codex 的 skills 目录即可被自动发现：

```bash
# 复制到用户级 skills 目录
mkdir -p ~/.codex/skills
cp -r gpt-image2-generator ~/.codex/skills/
```

## 脚本说明

`scripts/generate_image.py` 主体仅使用 Python 标准库；`--composite` 需要可选依赖 Pillow（`pip install pillow`）。
- 生成：`POST /v1/images/generations`（JSON：model / prompt / size / n / quality）
- 编辑：`POST /v1/images/edits`（JSON：model / prompt / images[].image_url，本地文件自动转 data URL；蒙版为 images[].mask_url）
- base_url 自动兼容三种写法：`https://host/`、`https://host/v1`、`https://host/v1/images/generations`
