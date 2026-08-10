# gpt-image2-generator

通过 OpenAI 兼容网关的 Images API 生成、编辑和拼合 `gpt-image-2` 图片，适合无法直接使用 `/v1/responses` 图片能力的客户端。

## 功能

- 调用 `/v1/images/generations` 生成图片
- 调用 `/v1/images/edits` 编辑图片
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

不要将真实网关地址或 API Key 提交到仓库、日志或公开回复中。
