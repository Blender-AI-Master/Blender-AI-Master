# Blender-AI Plugin → Backend API Contract

> 给后端团队的实现规范。**Base URL**: `https://api.blender-ai.com`
> **认证方式**: `Authorization: Bearer <KEY>` (KEY 在用户 dashboard 申请)
> **Content-Type**: `application/json`
> **错误响应**: HTTP 4xx/5xx + JSON `{ "error": "...", "code": "..." }`

---

## 1. 鉴权 & 账户

### `POST /v1/auth/validate`
验证 KEY 有效性,返回账户概况。**这是插件安装后第一次必须调的端点。**

Request body: `{}`

Response 200:
```json
{
  "email": "user@example.com",
  "plan": "pro",
  "balance": 12.50,
  "currency": "USD",
  "is_active": true,
  "expires_at": "2026-12-31T23:59:59Z"
}
```

错误:
- `401` `{ "error": "Invalid or expired key" }` → 提示用户重新填 KEY

### `GET /v1/account`
同 `/auth/validate`,但额外返回账户创建时间、消费历史摘要等。

Response 200:
```json
{
  "email": "user@example.com",
  "plan": "pro",
  "balance": 12.50,
  "currency": "USD",
  "is_active": true,
  "expires_at": "2026-12-31T23:59:59Z",
  "created_at": "2025-01-15T08:00:00Z",
  "lifetime_spent": 87.30
}
```

### `GET /v1/account/usage?limit=20`
消费历史(用于插件内"最近活动"面板,可选)。

Response 200:
```json
{
  "usage": [
    {
      "ts": "2026-06-15T10:23:00Z",
      "type": "model_generation",
      "model": "hunyuan3d",
      "amount": 0.80,
      "currency": "USD",
      "job_id": "abc123"
    }
  ]
}
```

### `GET /v1/pricing`
当前模型价格表(插件启动时拉一次缓存)。

Response 200:
```json
{
  "models": [
    {
      "id": "hunyuan3d",
      "display_name": "Hunyuan 3D",
      "price_per_call": 0.80,
      "currency": "USD",
      "description": "Generate realistic 3D model from text or image"
    },
    {
      "id": "creative-agent",
      "display_name": "Creative Agent (CLI-Anything)",
      "price_per_call": 0.05,
      "currency": "USD",
      "description": "Natural language → Blender commands"
    }
  ]
}
```

---

## 2. 3D 模型生成

### `POST /v1/models/generate`
提交一个 3D 生成任务。**调用前无需查余额** — 服务端会在执行前预扣费,失败退款。

Request:
```json
{
  "model": "hunyuan3d",
  "mode": "image2d",        // "text2d" | "image2d" | "hybrid"
  "prompt": "a wooden chair",  // 可选
  "image_base64": "iVBORw0...", // base64, 可选
  "face_count": 30000       // 可选,默认 30000
}
```

Response 202 (任务已受理):
```json
{
  "job_id": "j-abc123",
  "status": "WAIT",
  "charged": 0.80,
  "balance_after": 11.70
}
```

错误:
- `402 Payment Required` `{ "error": "Insufficient balance", "required": 0.80, "balance": 0.10 }` → 提示充值
- `400` `{ "error": "Invalid image" }` → 图片问题
- `429` `{ "error": "Rate limit exceeded" }` → 限流

### `GET /v1/models/jobs/{job_id}`
查询任务状态。

Response 200:
```json
{
  "job_id": "j-abc123",
  "status": "DONE",            // WAIT | RUN | DONE | FAIL
  "result": {
    "format": "glb",           // "glb" | "obj_zip"
    "size_bytes": 2345678
  },
  "charged": 0.80,
  "error": null
}
```

### `GET /v1/models/jobs/{job_id}/download`
下载结果。**返回二进制流**(Content-Type: `model/gltf-binary` 或 `application/zip`)。

Response 200: 二进制文件流
Response 402: `{ "error": "..." }` (理论上不会到这里,因为 submit 时已扣费)

---

## 3. LLM 代理 (Creative Agent)

### `POST /v1/chat/completions`
插件的"AI 对话"功能走这个端点。**后端根据请求体选择 LLM 并计费。**

Request:
```json
{
  "model": "auto",            // 后端路由:creative-agent / claude / gpt-4o / etc
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "帮我做一个机器人" }
  ],
  "temperature": 0.7,
  "max_tokens": 4096
}
```

Response 200:
```json
{
  "content": "## CLI Commands\nscene new --name robot\n...\n## End Commands",
  "model_used": "creative-agent",
  "usage": {
    "prompt_tokens": 234,
    "completion_tokens": 1024,
    "cost": 0.05
  },
  "balance_after": 11.65
}
```

错误:
- `402` → 余额不足
- `429` → 限流
- `503` → LLM 上游暂不可用

---

## 4. 错误码汇总

| HTTP | 含义 | 插件应展示 |
|------|------|-----------|
| 400 | 请求参数错误 | "请求格式错误: {error}" |
| 401 | KEY 无效/已过期 | "API Key 无效,请重新填写" |
| 402 | 余额不足 | "账户余额不足,请前往 blender-ai.com 充值" |
| 403 | KEY 已被禁用 | "账户已停用,请联系 support@blender-ai.com" |
| 404 | 资源不存在 | "任务不存在" |
| 429 | 限流 | "请求过于频繁,请稍后再试" |
| 500/502/503 | 服务异常 | "服务暂时不可用,请稍后重试" |
| 网络错误 | 无连接 | "网络错误,请检查连接" |

---

## 5. 用户引导链接

| 用途 | URL |
|------|-----|
| 注册/获取 KEY | `https://www.blender-ai.com/dashboard/api-keys` |
| 账户 & 充值 | `https://www.blender-ai.com/dashboard/settings?section=account` |
| 消费历史 | `https://www.blender-ai.com/dashboard/billing` |
| 我的模型 | `https://www.blender-ai.com/dashboard/models` |
| 客服 | `support@blender-ai.com` |

---

## 6. 实现建议 (后端)

1. **KEY 格式**: `sk-cp-` 开头 + 32 字符 base62,例如 `sk-cp-1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p`
2. **扣费策略**: submit 任务时**预扣** `pricing[model].price_per_call`,任务失败时**原路退款**。
3. **幂等性**: `POST /v1/models/generate` 接受 `Idempotency-Key` 请求头(用 `job_id` 客户端生成),防止用户重试时重复扣费。
4. **限流**: 按 KEY 限流,默认 60 req/min,生成任务单独限流 10 req/min。
5. **审计日志**: 每次扣费写一条 `usage` 记录,字段:ts / key_id / type / model / amount / job_id / status。
