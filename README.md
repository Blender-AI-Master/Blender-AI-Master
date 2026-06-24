# Blender AI Assistant - AI-powered Blender 3D Modeling Plugin

**AI 驱动的 Blender 3D 建模插件 —— 用自然语言指挥创意实现,统一 KEY 登录,按次扣费**

## Features

- **One Key Sign-in** - 用一个 blender-ai.com API Key 即可使用所有 AI 功能
- **Pay Per Use** - 每次生成自动从账户余额扣费,无需配置多家 API
- **Natural Language Modeling** - 在 Blender 里直接说 "做一个低多边形山地",AI 自动生成 CLI 命令并执行
- **Real-time Preview** - 命令同步到 Blender 视口,实时看到模型
- **3D Generation** - 文生 3D / 图生 3D,主流模型(Hunyuan 3D 等)开箱即用

## Quick Start (新用户)

1. **安装插件**:Blender → Edit → Preferences → Extensions → Install from Disk → 选 `dist\blender-ai-assistant-2.6.0.zip`
2. **启动后端** (首次或换电脑时):运行 `.\plugin\scripts\dev-up.ps1`,后端会监听 `http://localhost:3000` (或 3100,看 `.env`)
3. **获取本地 Key**:在另一个终端执行
   ```powershell
   cd website\Blender_AI_Master_H
   npm run db:create-key -- --email you@example.com --topup 50
   ```
   复制输出的 `sk-cp-xxxxxxxx...`
4. **填入 Key**:Edit → Preferences → Extensions → AI Assistant for Blender
   - **API Key**:粘贴上面那个 `sk-cp-...`
   - **API Server**:选 `Local Dev (http://localhost:3000)` (默认就是这个)
   - 点 **测试 & 登录** → 应该看到邮箱 + $50 余额
5. **开始创作**:3D 视图侧栏 → AI 助手 → 输入描述 / 选图 → 点 "生成 3D 模型"

> **生产用户**:如果你想用官方线上服务,把 **API Server** 切到 `Production (www.blender-ai.com:8443)` 并去 https://www.blender-ai.com/dashboard/api-keys 申请 Key。
> 生产环境的部署见 [`docs/DEPLOY.md`](docs/DEPLOY.md)。

### API Server 选项

| 选项 | 地址 | 用途 |
|------|------|------|
| `Local Dev` (默认) | `http://localhost:3000` | 本机 `dev-up.ps1` 启动的后端 |
| `Production` | `https://www.blender-ai.com:8443` | 官方线上服务(需联网 + Key 申请) |

> **新装用户**:默认是 `Local Dev`,需要本机后端在 `localhost:3000` (或 `.env` 里的端口) 监听。
> **生产部署完成后**:可以手动切到 `Production`。
> 切换后,Base URL 会即时显示在选择器下方(箭头 `→ http://localhost:3000`)。

## Architecture

```
User Input → blender-ai.com 代理 → 上游 AI (Hunyuan3D / Claude / OpenAI / ...)
     ↓
每调用一次 → 预扣费 → 任务完成 → 结算 → https://www.blender-ai.com/dashboard/settings?section=account
```

### Key Components

| Component | Description |
|-----------|-------------|
| `api/playground.py` | 统一鉴权/计费 API 客户端 (PlaygroundAPI) |
| `core/billing.py` | 账户信息缓存 / 错误格式化 / Operator 装饰器 |
| `AIAI_OT_sign_in` | 登录验证 |
| `AIAI_OT_generate` | 3D 模型生成 (走代理) |
| `AIAI_OT_send_chat` | LLM 对话 (走代理) |
| `AIAI_PT_panel._draw_account_box` | 顶部账户状态卡 (余额/套餐/充值入口) |

## Requirements

- Blender 4.2+ (测试到 6.0)
- Node.js 20+ (仅当你要跑本地后端)
- 一个有效的 API Key:
  - 本地:用 `npm run db:create-key` 生成
  - 生产:去 https://www.blender-ai.com/dashboard/api-keys 申请

## Configuration

**插件唯一配置项**:
- **AddonPreferences.playground_api_key** - 你的 API Key
- **AddonPreferences.api_server** - `Local Dev` (默认) 或 `Production`

其他 scene-level 属性 (如 `tsr_face_count`, `tsr_prompt_text` 等) 用于控制生成参数。

## Pricing

| 模型 | 单价 | 计费方式 |
|------|------|----------|
| Hunyuan 3D | $0.80 / 次 | 提交任务时预扣,失败退款 |
| Creative Agent (CLI-Anything) | $0.05 / 次 | 发送对话时结算 |
| 其他模型 | 见 https://www.blender-ai.com/dashboard/settings?section=account | |

## Error Handling

| 错误 | 含义 | 用户操作 |
|------|------|----------|
| 401 Invalid Key | KEY 无效或已过期 | 重新填 KEY |
| 402 Insufficient Balance | 余额不足 | 去 dashboard 充值 |
| 403 Account Inactive | 账户被停用 | 联系 support@blender-ai.com |
| 429 Rate Limited | 请求过频 | 稍等几秒 |
| 网络错误 | 无法连接 | 检查网络 / 后端是否启动 |

## Repository Layout

```
BlenderAiMaster\
├── plugin\                          ← Blender 插件 (Python)
│   ├── __init__.py                  ← 入口 (operators + panel)
│   ├── blender_manifest.toml        ← 扩展清单 (Blender 4.2+)
│   ├── api\                         ← 后端 API 客户端
│   │   ├── playground.py            ← KEY 鉴权 + 计费
│   │   ├── llm.py                   ← LLM 对话
│   │   ├── hunyuan.py               ← Hunyuan 3D
│   │   └── opencode_provider.py
│   ├── core\
│   │   ├── billing.py               ← 账户缓存 + 装饰器
│   │   ├── cli_manager.py           ← CLI-Anything
│   │   └── apply_project.py
│   ├── cli_anything\                ← CLI-Anything 框架代码
│   ├── scripts\
│   │   ├── dev-up.ps1               ← 一键启动本地后端
│   │   ├── build-plugin.ps1         ← 打包 zip
│   │   ├── start-https-local.ps1    ← 本地 HTTPS 代理 (模拟生产)
│   │   └── https-proxy.mjs          ← Node HTTPS 反代
│   ├── deploy\
│   │   ├── nginx-8443.conf          ← 生产 nginx API 配置
│   │   └── nginx-443.conf           ← 生产 nginx 前端配置
│   ├── docs\
│   │   ├── BACKEND_API.md           ← 插件↔后端 API 合约
│   │   └── DEPLOY.md                ← 完整生产部署指南
│   ├── install.ps1 / install.bat    ← Windows 一键安装
│   └── dist\
│       └── blender-ai-assistant-2.6.0.zip   ← 打包好的插件
│
└── website\
    ├── blender-ai-master\           ← 前端 (Vite + React 19)
    │   ├── src\                     ← React 应用
    │   ├── package.json
    │   └── dist\                    ← npm run build 产物
    │
    └── Blender_AI_Master_H\         ← 后端 (Hono + Drizzle + SQLite)
        ├── src\                     ← API server
        ├── drizzle\                 ← DB schema 迁移
        ├── scripts\                 ← create-key / seed
        ├── certs\                   ← DigiCert 证书 (blender-ai.com)
        ├── data.db                  ← SQLite 数据库
        ├── .env                     ← 本地配置
        ├── Dockerfile
        └── package.json
```

## Development

后端 API 合约见 [`docs/BACKEND_API.md`](docs/BACKEND_API.md)。
如果后端端点有差异,只需修改 `api/playground.py` 顶部的:
- `PRODUCTION_BASE_URL` - 生产 API 地址
- `LOCAL_BASE_URL` - 本地 API 地址
- `API_VERSION` - API 版本
- 各方法中的 `path` 参数

### Local Development

本机运行完整后端 + 插件调试,无需 Vercel/云服务。

#### Prerequisites

- [Node.js 20+](https://nodejs.org/) (后端用)
- 任何 SQLite 客户端 (Drizzle 自带 `db:studio`)

#### One-Command Startup

```powershell
# 在项目根目录运行
.\plugin\scripts\dev-up.ps1
```

这会自动:
1. 安装后端 Node 依赖 (到 `website/Blender_AI_Master_H/node_modules`)
2. 从 `.env.example` 创建 `.env` (如果还没有)
3. 推送数据库 schema + 灌入定价
4. 启动后端 dev server (默认 `http://localhost:3000` 或 `.env` 里的 `PORT`)

#### Create Test API Key

```powershell
cd website\Blender_AI_Master_H
npm run db:create-key -- --email you@example.com --topup 50
```

输出类似:
```
KEY: sk-cp-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Save this! It will not be shown again.
Topped up: $50.00
```

#### Run Plugin Against Local Backend

1. 打开 Blender → Edit → Preferences → Extensions → AI Assistant for Blender
2. 粘贴上面得到的 `sk-cp-...` KEY
3. **API Server 选择 "Local Dev"** (默认就是这个)
4. 点 **测试 & 登录** → 应该看到邮箱 + $50 余额
5. 3D 视图侧栏 → AI 助手 → 开始生成

#### Simulate Production HTTPS Locally (optional)

如果你想在本地用 `https://www.blender-ai.com:8443` (production 模式) 而不是 `http://localhost:3000`,在另一个终端:

```powershell
.\plugin\scripts\start-https-local.ps1 -Port 8443 -Upstream http://127.0.0.1:3000
```

然后 Blender 里 **API Server = Production** (因为 `https://www.blender-ai.com:8443` 是默认 production URL)。
证书用的是 `website\Blender_AI_Master_H\certs\blender-ai.com.pem` (DigiCert 签发的真证书,Python urllib 和 Chromium 都信任)。

#### Build Plugin Zip

```powershell
# 在项目根目录
.\plugin\scripts\build-plugin.ps1
# → plugin\dist\blender-ai-assistant-2.6.0.zip
```

#### One-Click Install on Windows (Blender 5.1)

```powershell
.\plugin\install.ps1
```

会自动:
1. 清理旧的 `cli_anything_blender` 残留
2. 备份并清空 `userpref.blend` (清缓存)
3. 打包 zip 到 `%TEMP%\cli_anything_blender_v3.zip`
4. 用 Blender headless 模式装载并启用插件 (自动处理 license 字段)
5. 提示重启 Blender

## License

MIT License

## Acknowledgments

- [OpenCode AI](https://github.com/opencode-ai/opencode) - 多轮思考 Agent (v2.5 及之前使用)
- [CLI-Anything](https://github.com/TripoAI/cli-anything) - Blender 命令行框架
- [blender-ai.com](https://www.blender-ai.com/) - 统一 API 代理 & 计费服务
