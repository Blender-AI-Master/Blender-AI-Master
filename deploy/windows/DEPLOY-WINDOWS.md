# Blender-AI Master — Production Deployment on **Windows Server 2025**

> 用 nginx (Windows) 做反代,Node API 包成 Windows Service (NSSM),DigiCert 证书做 HTTPS。

## 0. 资源清单 (服务器 `WIN-DJ2Q4A986AB`)

| 资源 | 要求 |
|---|---|
| OS | Windows Server 2025 Datacenter (你已经有了) |
| 内存 | 64 GB ✓ |
| 端口 | 80, 443, 8443 (对外开放) / 3001 (Node API,只绑 127.0.0.1) |
| 软件 | Node.js 20+ LTS, Git for Windows (带 openssl) |
| 证书 | DigiCert `blender-ai.com` (.pfx 或 .pem+.key) |
| 必需的 key | `HUNYUAN_SECRET_ID` / `HUNYUAN_SECRET_KEY` / `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` |

## 1. 一次性服务器准备 (RDP 进去,管理员 PowerShell)

```powershell
# 1.1 装 Node.js 20 LTS
#  从 https://nodejs.org 下载 Windows 安装包,默认下一步,完成后重启 shell

# 1.2 装 Git for Windows (带 openssl)
#  https://git-scm.com/download/win, 默认下一步

# 1.3 关闭 IE Enhanced Security (不然 curl 经常被拦)
$ie = "HKLM:\SOFTWARE\Microsoft\Active Setup\Installed Components\{A509B1A7-37EF-4b3c-8C71-4B3D3F4B4D1B}"
Set-ItemProperty -Path $ie -Name "IsInstalled" -Value 0 -ErrorAction SilentlyContinue

# 1.4 创建部署目录
New-Item -ItemType Directory -Path "C:\blender-ai" -Force
New-Item -ItemType Directory -Path "C:\blender-ai\logs" -Force
New-Item -ItemType Directory -Path "C:\blender-ai\certs" -Force
```

## 2. 把代码推到服务器

**方式 A: 在本机 (你当前 dev 机器) 用 robocopy 推 (需在同一个网段)**
```powershell
# 在本机 PowerShell
$source = "I:\Projects-2026\BlenderAiMaster"
$dest   = "\\WIN-DJ2Q4A986AB\C$\blender-ai\src"
# 先 rsync 一份(不跑 build),再去服务器上跑 copy-source.ps1
robocopy $source $dest /MIR /XD node_modules dist .git /XF "*.zip" 2>&1 | Out-Null
```

**方式 B: 在服务器上 copy-source.ps1 (推荐)**
1. 把 `plugin\deploy\windows\` 整个目录拷到服务器 `C:\blender-ai\setup\`
2. RDP 到服务器,管理员 PowerShell:
   ```powershell
   cd C:\blender-ai\setup
   # SourceDir 是你 git clone / scp 上传的源位置
   .\copy-source.ps1 -SourceDir C:\path\to\BlenderAiMaster -DestDir C:\blender-ai
   ```
3. 这一步会把:
   - `website\Blender_AI_Master_H\` → `C:\blender-ai\api\`
   - `website\blender-ai-master\dist\` → `C:\blender-ai\frontend\`
   - 后端跑 `npm ci` + `npm run build`

## 3. 改后端 .env

在 `C:\blender-ai\api\.env` 填:

```ini
DATABASE_URL=file:./data.db
PORT=3001
NODE_ENV=production
LOG_LEVEL=info
CORS_ORIGINS=https://www.blender-ai.com,https://localhost:8443

STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
PUBLIC_SITE_URL=https://www.blender-ai.com

HUNYUAN_SECRET_ID=AKID...
HUNYUAN_SECRET_KEY=...
HUNYUAN_REGION=ap-guangzhou

OPENAI_API_KEY=
ANTHROPIC_API_KEY=
...

REFUND_STUCK_HOURS=24
RATE_LIMIT_PER_KEY_PER_MIN=60
RATE_LIMIT_GENERATION_PER_MIN=10
```

## 4. 装后端为 Windows Service

```powershell
cd C:\blender-ai\setup
.\install-api-service.ps1
# 第一次会下载 NSSM (~600 KB) 到 C:\Tools\nssm
# 完成后 blender-ai-api 服务自动启动,绑 127.0.0.1:3001
```

验证:
```powershell
Get-Service blender-ai-api    # 应 Running
curl http://127.0.0.1:3001/health   # {"ok":true,...}
Get-Content C:\blender-ai\logs\api-stdout.log -Tail 20
```

## 5. 装 nginx + 证书 + 反代

```powershell
cd C:\blender-ai\setup

# 5.1 如果有 DigiCert .pfx:
$env:CERT_PFX_PASSWORD = "你的 pfx 密码"
.\import-cert.ps1 -PfxPath D:\transfer\blender-ai.com.pfx
#  会把证书导入 LocalMachine\My,并导出 PEM 给 nginx 用
#  完成后: Restart-Service nginx

# 5.2 没有真证书,先用自签 (开发用):
#  install-nginx.ps1 会自动生成一个一年的自签 cert
#  (浏览器会报不安全,但 Python urllib 默认信任系统证书库,所以插件用没事)
#  ⚠️  上线前必须换成 DigiCert

# 5.3 装 nginx:
.\install-nginx.ps1
#  - 下载 nginx-1.27.5 (~2 MB) 到 C:\nginx
#  - 生成配置文件 (frontend 443 / API 8443 / 80→443)
#  - 用 NSSM 注册为 Windows Service (auto-start, 自动重启)
#  - 打开防火墙 TCP 80/443/8443
```

## 6. DNS 指向

把 `www.blender-ai.com` 的 A 记录指向 `WIN-DJ2Q4A986AB` 的公网 IP。

## 7. 验证

```powershell
# 本机
curl -k https://127.0.0.1:443/                  # 静态站
curl -k https://127.0.0.1:8443/health           # API health
curl -k -X POST https://127.0.0.1:8443/v1/auth/register `
     -H "Content-Type: application/json" `
     -Body '{"email":"first@blender-ai.com","password":"change-me-123"}'
# → 201, $5.00 welcome bonus,返回 api_key

# 域名通了以后,从外网
curl https://www.blender-ai.com/
curl https://www.blender-ai.com:8443/health
```

## 8. 创建生产 API Key (给用户)

```powershell
cd C:\blender-ai\api
npm run db:create-key -- --email vip@customer.com --topup 50
# 输出 sk-cp-XXXXX,把这个发给用户
```

## 9. 服务管理速查

```powershell
# 后端
Get-Service blender-ai-api
Restart-Service blender-ai-api
Stop-Service blender-ai-api
Get-Content C:\blender-ai\logs\api-stdout.log -Wait

# nginx
Get-Service nginx
Restart-Service nginx
# 配置改了以后
& "C:\nginx\nginx.exe" -s reload
Get-Content C:\nginx\logs\error.log -Tail 30

# 防火墙
Get-NetFirewallRule -DisplayName "Blender-AI*"
```

## 10. 升级流程

```powershell
# 10.1 本机
cd I:\Projects-2026\BlenderAiMaster
git pull
# 改完代码后:
cd website\Blender_AI_Master_H
npm run build
cd ..\blender-ai-master
npm run build
# 打包 plugin zip
cd ..\..\plugin
.\scripts\build-plugin.ps1

# 10.2 推到服务器 (在服务器上跑)
cd C:\blender-ai\setup
.\copy-source.ps1 -SourceDir C:\path\to\new\BlenderAiMaster -DestDir C:\blender-ai
Restart-Service blender-ai-api
# frontend 是 dist 静态文件,直接覆盖即可,不需要重启 nginx
```

## 11. 续证书 (每 3 个月)

```powershell
cd C:\blender-ai\setup
$env:CERT_PFX_PASSWORD = "新 pfx 密码"
.\import-cert.ps1 -PfxPath D:\transfer\blender-ai.com-new.pfx
Restart-Service nginx
# 验证
curl -vI https://www.blender-ai.com/ 2>&1 | findstr "expire\|issuer"
```

## 12. 故障排查

| 现象 | 查什么 | 怎么修 |
|---|---|---|
| `curl :443` 没响应 | `Get-Service nginx`, `Get-Content C:\nginx\logs\error.log -Tail 30` | `Restart-Service nginx` |
| `curl :8443/health` 502 | `Get-Service blender-ai-api`, `Get-Content C:\blender-ai\logs\api-stderr.log -Tail 30` | 看后端日志;`.env` 里的 `PORT=3001` 对不对 |
| 401 登录失败 | DB 里有没有这个 user | `cd C:\blender-ai\api && npm run db:create-key -- --email ...` |
| 浏览器报 `NET::ERR_CERT_AUTHORITY_INVALID` | cert 是自签的 | 跑第 5.1 换成 DigiCert |
| `npm run dev` 报 EADDRINUSE | :3001 已被占 | `Stop-Service blender-ai-api` 或 `Get-NetTCPConnection -LocalPort 3001` |
| firewall 拦了 | `Test-NetConnection -Port 443` | `Get-NetFirewallRule -DisplayName "Blender-AI*"` 确认规则存在 |

## 附:目录结构 (部署后)

```
C:\blender-ai\
├── api\                 ← Node 后端 (3001)
│   ├── .env
│   ├── dist\index.js
│   ├── data.db
│   └── ...
├── frontend\            ← Vite 静态站 (nginx 直接 serve)
│   ├── index.html
│   └── assets\
├── certs\               ← 证书 (PEM for nginx, PFX in LocalMachine\My)
│   ├── blender-ai.com.pem
│   ├── blender-ai.com.key
│   └── ...
├── logs\
│   ├── api-stdout.log
│   ├── api-stderr.log
│   └── (nginx 自己的在 C:\nginx\logs\)
└── setup\               ← 这些 .ps1 部署脚本
    ├── copy-source.ps1
    ├── install-api-service.ps1
    ├── install-nginx.ps1
    └── import-cert.ps1
```
