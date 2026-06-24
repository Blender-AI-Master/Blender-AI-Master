// https-proxy.mjs
// ---------------------------------------------------------------
// Local HTTPS reverse proxy:  https://0.0.0.0:8443  →  http://127.0.0.1:<upstream>
// Goal: 让 plugin 在本地也能用 "Production" 模式 (https://www.blender-ai.com:8443)
//       做端到端联调,无需部署到真实服务器。
//
// Usage:
//   1. 准备好证书 (PEM + KEY) 和 upstream 端口
//   2. node scripts/https-proxy.mjs
//   3. 浏览器访问 https://localhost:8443/health 验证
//
// Env vars (with defaults):
//   PORT        8443
//   UPSTREAM    http://127.0.0.1:3000
//   CERT_FILE   ../../website/Blender_AI_Master_H/certs/blender-ai.com.pem
//   KEY_FILE    ../../website/Blender_AI_Master_H/certs/blender-ai.com.key
//   CA_FILE     (optional, for client cert verification; usually empty)
//
// Note: certs/ 里现成的 blender-ai.com.pem 是 DigiCert 签发的真实证书
//       (Subject: CN=blender-ai.com),Python urllib + Chromium 都会信任。
//       本地仅用于模拟生产 endpoint,真生产部署请把同一证书放到服务器。
// ---------------------------------------------------------------

import { createServer } from "node:https";
import { readFileSync, existsSync } from "node:fs";
import { createServer as createHttpServer } from "node:http";
import { request as httpRequest } from "node:http";
import { request as httpsRequest } from "node:https";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot  = join(__dirname, "..", "..");

const PORT     = Number(process.env.PORT     || 8443);
const UPSTREAM = process.env.UPSTREAM || "http://127.0.0.1:3000";
const CERT_FILE = process.env.CERT_FILE || join(repoRoot, "website", "Blender_AI_Master_H", "certs", "blender-ai.com.pem");
const KEY_FILE  = process.env.KEY_FILE  || join(repoRoot, "website", "Blender_AI_Master_H", "certs", "blender-ai.com.key");

for (const p of [CERT_FILE, KEY_FILE]) {
  if (!existsSync(p)) {
    console.error(`[FATAL] Cert/key not found: ${p}`);
    process.exit(1);
  }
}

const upstreamUrl = new URL(UPSTREAM);
const proxyRequest = upstreamUrl.protocol === "https:" ? httpsRequest : httpRequest;

const server = createServer(
  {
    cert: readFileSync(CERT_FILE),
    key:  readFileSync(KEY_FILE),
    // HSTS — once the client visits once, future visits must be HTTPS
    // (only meaningful if the cert is trusted, which it is for blender-ai.com)
  },
  (req, res) => {
    const start = Date.now();
    const headers = { ...req.headers };
    delete headers.host; // let upstream receive its own host header

    const proxyReq = proxyRequest(
      {
        hostname: upstreamUrl.hostname,
        port:     upstreamUrl.port || (upstreamUrl.protocol === "https:" ? 443 : 80),
        path:     req.url,
        method:   req.method,
        headers,
      },
      (proxyRes) => {
        res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
        proxyRes.pipe(res);
        console.log(`[${new Date().toISOString()}] ${req.method} ${req.url} → ${proxyRes.statusCode} (${Date.now() - start}ms)`);
      }
    );

    proxyReq.on("error", (err) => {
      console.error(`[ERROR] upstream ${UPSTREAM} failed: ${err.message}`);
      if (!res.headersSent) {
        res.writeHead(502, { "Content-Type": "application/json" });
      }
      res.end(JSON.stringify({ error: "Bad Gateway", upstream: UPSTREAM, detail: err.message }));
    });

    req.pipe(proxyReq);
  }
);

// 8443 通常需要 root;Windows 上 Node 直接 listen 即可
server.listen(PORT, "0.0.0.0", () => {
  console.log(`[https-proxy] listening on https://0.0.0.0:${PORT}`);
  console.log(`[https-proxy] upstream: ${UPSTREAM}`);
  console.log(`[https-proxy] cert:     ${CERT_FILE}`);
  console.log(`[https-proxy] key:      ${KEY_FILE}`);
  console.log("");
  console.log("Plugin test:");
  console.log(`  In Blender, set API Server = Production (or local_dev pointing here)`);
  console.log(`  Base URL = https://localhost:${PORT}`);
  console.log("");
  console.log("Press Ctrl+C to stop");
});

process.on("SIGINT",  () => { console.log("\n[shutdown]"); server.close(() => process.exit(0)); });
process.on("SIGTERM", () => { console.log("\n[shutdown]"); server.close(() => process.exit(0)); });
