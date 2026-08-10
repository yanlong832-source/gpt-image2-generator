# gpt-image2-generator

通过 OpenAI 兼容网关的 Images API 生成、编辑和拼合 `gpt-image-2` 图片，适合无法直接使用 `/v1/responses` 图片能力的客户端。

## 功能

- 调用 `/v1/images/generations` 生成图片
- 调用 `/v1/images/edits` 编辑图片，支持 JSON data URL 或 multipart 文件上传
- 支持多图网格拼合
- 首次使用自动创建 `~/.gpt-image2/config.json` 配置模板
- 通过 `--preview` 输出可直接渲染的本地 Markdown 预览链接

## 首次使用

直接运行生成命令即可。若未设置环境变量且配置文件不存在，脚本会创建空模板并显示实际路径：

```json
{
  "base_url": "",
  "api_key": ""
}
```

在 `~/.gpt-image2/config.json` 中填入网关地址和密钥后重新运行。也可以改用环境变量 `GPT_IMAGE_API_BASE_URL` 与 `GPT_IMAGE_API_KEY`；环境变量优先。

## 示例

```bash
python scripts/generate_image.py \
  --prompt "一只戴帽子的橘猫，油画风格" \
  --size 1024x1536 \
  --preview
```

## 编辑接口兼容性

默认编辑请求使用 JSON 的 `images[].image_url` 字段：本地文件会转为 data URL，图片 URL 会原样传递。适用于支持 JSON Images API 的网关：

```bash
python scripts/generate_image.py \
  --edit 原图.png \
  --prompt "把背景换成蓝色" \
  --output 蓝色背景.png \
  --preview
```

若网关仅接受 OpenAI 风格的 `multipart/form-data` 上传，请显式传入 `--edit-transport multipart`。此模式发送 `image` 文件字段，蒙版发送 `mask` 文件字段；两者都必须是本地文件，不能使用图片 URL：

```bash
python scripts/generate_image.py \
  --edit 原图.png \
  --mask 蒙版.png \
  --edit-transport multipart \
  --prompt "只把背景换成蓝色" \
  --output 蓝色背景.png \
  --preview
```

不要将真实网关地址或 API Key 提交到仓库、日志或公开回复中。
