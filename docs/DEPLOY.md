# Blender-AI Production Deployment Guide

> 把本机开发好的后端 + 前端 + 插件 zip 部署到生产环境 (`blender-ai.com`) 的完整流程。

## 0. 资源清单

| 资源 | 来源 |
|---|---|
| 服务器 | Ubuntu 22.04+ / Debian 12+,root 权限 |
| 域名 | `www.blender-ai.com` (DNS A 记录已指向服务器 IP) |
| 证书 | DigiCert 签发的 `blender-ai.com.pem` + `.key` (3 个月有效,需定期续) |
| Node.js | 20+ (`node -v` ≥ v20) |
| 端口 | 80 / 443 (前端+HTTPS) , 8443 (API) , 3001 (Node 内部,只 bind 127.0.0.1) |
| 必需的 API key | `HUNYUAN_SECRET_ID` / `HUNYUAN_SECRET_KEY` / `STRIPE_SECRET_KEY` |

## 1. 部署代码

```bash
# 服务器上
adduser --system --group blender-ai
mkdir -p /opt/blender-ai
cd /opt

# 二选一:
#   a) git 拉取 (推荐)
git clone https://github.com/Blender-AI-Master/BlenderAiMaster.git
#   b) rsync 从本机推送
rsync -avz --exclude 'node_modules' --exclude 'dist' --exclude '.git' \
    ./BlenderAiMaster/ root@blender-ai.com:/opt/blender-ai/BlenderAiMaster/
```

## 2. 部署后端

```bash
cd /opt/blender-ai/BlenderAiMaster/website/Blender_AI_Master_H
cp .env.example .env
nano .env       # ← 必须改的:
                #    PORT=3001
                #    NODE_ENV=production
                #    DATABASE_URL=file:/var/lib/blender-ai/data.db
                #    HUNYUAN_SECRET_ID=...
                #    HUNYUAN_SECRET_KEY=...
                #    STRIPE_SECRET_KEY=sk_live_...
                #    STRIPE_WEBHOOK_SECRET=whsec_...
                #    PUBLIC_SITE_URL=https://www.blender-ai.com

npm ci
npm run build                       # ts/dist/index.js
npm run db:push                     # 建表 (第一次)
npm run db:seed                     # 灌定价
```

## 3. systemd service

```bash
cat > /etc/systemd/system/blender-ai-api.service <<'EOF'
[Unit]
Description=Blender-AI Master API
After=network.target

[Service]
Type=simple
User=blender-ai
WorkingDirectory=/opt/blender-ai/BlenderAiMaster/website/Blender_AI_Master_H
EnvironmentFile=/opt/blender-ai/BlenderAiMaster/website/Blender_AI_Master_H/.env
ExecStart=/usr/bin/node --env-file=/opt/blender-ai/BlenderAiMaster/website/Blender_AI_Master_H/.env dist/index.js
Restart=always
RestartSec=3
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now blender-ai-api
systemctl status blender-ai-api
curl http://127.0.0.1:3001/health   # → {"ok":true,...}
```

## 4. 部署前端

```bash
cd /opt/blender-ai/BlenderAiMaster/website/blender-ai-master
npm ci
npm run build                       # → dist/
mkdir -p /var/www/blender-ai
cp -r dist/* /var/www/blender-ai/
chown -R blender-ai:blender-ai /var/www/blender-ai
```

(前端 `VITE_API_BASE` 等 env 在打包前要写对,默认 `https://www.blender-ai.com:8443`。)

## 5. 部署证书

```bash
mkdir -p /etc/nginx/ssl/blender-ai.com
# 从本机 website/Blender_AI_Master_H/certs/ 上传:
scp certs/blender-ai.com.pem root@blender-ai.com:/etc/nginx/ssl/blender-ai.com/
scp certs/blender-ai.com.key root@blender-ai.com:/etc/nginx/ssl/blender-ai.com/
chmod 600 /etc/nginx/ssl/blender-ai.com/blender-ai.com.key
```

## 6. 部署 nginx

```bash
ln -sf /opt/blender-ai/BlenderAiMaster/plugin/deploy/nginx-8443.conf \
       /etc/nginx/conf.d/blender-ai-8443.conf
ln -sf /opt/blender-ai/BlenderAiMaster/plugin/deploy/nginx-443.conf \
       /etc/nginx/conf.d/blender-ai-443.conf
nginx -t
systemctl reload nginx
```

## 7. 防火墙

```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8443/tcp
# 3001 不对外开放 (只 bind 127.0.0.1)
```

## 8. 验证

```bash
# 健康检查
curl -k https://www.blender-ai.com:8443/health
# → {"ok":true,"ts":"..."}

# 创建一个 API Key (发邮件给早期用户)
cd /opt/blender-ai/BlenderAiMaster/website/Blender_AI_Master_H
npm run db:create-key -- --email vip@blender-ai.com --topup 100
# → 输出 sk-cp-XXXXX,把这个发给用户

# 用 KEY 试一下登录
curl -X POST https://www.blender-ai.com:8443/v1/auth/validate \
     -H "Authorization: Bearer sk-cp-XXXXX" \
     -H "Content-Type: application/json" \
     -d '{}'
```

## 9. 监控

```bash
journalctl -u blender-ai-api -f
tail -f /var/log/nginx/blender-ai-api.access.log
```

## 10. 续证书 (每 3 个月)

证书 6/5 → 9/2 过期;在过期前 2 周续。

```bash
certbot certonly --manual -d blender-ai.com -d www.blender-ai.com \
    --preferred-challenges dns        # DNS-01 验证,不依赖 80
# 把新 cert 拷到 /etc/nginx/ssl/blender-ai.com/
cp /etc/letsencrypt/live/blender-ai.com/fullchain.pem \
   /etc/nginx/ssl/blender-ai.com/blender-ai.com.pem
cp /etc/letsencrypt/live/blender-ai.com/privkey.pem \
   /etc/nginx/ssl/blender-ai.com/blender-ai.com.key
systemctl reload nginx
```

## 11. 升级

```bash
cd /opt/blender-ai/BlenderAiMaster
git pull
cd website/Blender_AI_Master_H
npm ci && npm run build
cd ../blender-ai-master
npm ci && npm run build && cp -r dist/* /var/www/blender-ai/
systemctl restart blender-ai-api
```

## 12. 本地模拟生产 (无需服务器)

想在 Windows / Mac 本机用 production 模式 (`https://www.blender-ai.com:8443`) 联调插件:

```powershell
# 终端 1: 起后端
.\plugin\scripts\dev-up.ps1

# 终端 2: 起 HTTPS 代理 (使用 certs/ 里现成的 DigiCert 证书)
.\plugin\scripts\start-https-local.ps1 -Port 8443 -Upstream http://127.0.0.1:3100
```

然后在 Blender 的插件偏好里:
- **API Server** = `Production` (或 `Local Dev` 改成 `https://localhost:8443`)
- **API Key** = 本机 `npm run db:create-key` 出来的 `sk-cp-...`
- 点 **测试 & 登录** → 应显示本地账户 + 余额

## 常见坑

| 现象 | 原因 | 修法 |
|---|---|---|
| `curl https://...:8443/health` 超时 | nginx 没起 / 没 reload | `nginx -t && systemctl reload nginx` |
| 502 Bad Gateway | Node API 没起 / PORT 配错 | `systemctl status blender-ai-api` ; `.env` 里 `PORT=3001` |
| 401 登录失败 | KEY 输错 / 用户表里没这 key | `npm run db:create-key -- --email ...` |
| 证书过期 | 3 个月到期 | 走第 10 步续证书 |
| 插件报 SSL error | cert 被 urllib 拒绝 | cert 必须是真 CA 签发 (DigiCert);本机模拟用 `certs/` 里现成那份 |
| 数据库锁死 | 多进程同时写 SQLite | 加 `set -e` 到 service,或换 Postgres |
