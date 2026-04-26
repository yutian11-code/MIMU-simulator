#!/usr/bin/env node
import fs from 'node:fs';
import http from 'node:http';
import https from 'node:https';
import net from 'node:net';

const listenHost = process.env.MIMU_HTTPS_HOST || '0.0.0.0';
const listenPort = Number(process.env.MIMU_HTTPS_PORT || 19443);
const certPath = process.env.MIMU_HTTPS_CERT || '/storage/nvme3/shushanfu/MIMU-colleague/var/certs/mimu-lan.crt';
const keyPath = process.env.MIMU_HTTPS_KEY || '/storage/nvme3/shushanfu/MIMU-colleague/var/certs/mimu-lan.key';
const frontendOrigin = new URL(process.env.MIMU_FRONTEND_ORIGIN || 'http://127.0.0.1:19006');
const backendOrigin = new URL(process.env.MIMU_BACKEND_ORIGIN || 'http://127.0.0.1:13000');

function stripApiPrefix(url) {
  const parsed = new URL(url || '/', 'https://mimu.local');
  const path = parsed.pathname.replace(/^\/api(?=\/|$)/, '') || '/';

  return `${path}${parsed.search}`;
}

function getTarget(req) {
  const parsed = new URL(req.url || '/', 'https://mimu.local');

  if (parsed.pathname === '/api' || parsed.pathname.startsWith('/api/')) {
    return {
      origin: backendOrigin,
      path: stripApiPrefix(req.url),
    };
  }

  return {
    origin: frontendOrigin,
    path: req.url || '/',
  };
}

function proxyHttpRequest(req, res) {
  const target = getTarget(req);
  const headers = {
    ...req.headers,
    host: target.origin.host,
    'x-forwarded-host': req.headers.host || '',
    'x-forwarded-proto': 'https',
  };

  const proxyReq = http.request(
    {
      hostname: target.origin.hostname,
      port: Number(target.origin.port || 80),
      method: req.method,
      path: target.path,
      headers,
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    }
  );

  proxyReq.on('error', (error) => {
    res.writeHead(502, { 'content-type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ message: `HTTPS gateway upstream failed: ${error.message}` }));
  });

  req.pipe(proxyReq);
}

function proxyUpgrade(req, socket, head) {
  const target = getTarget(req);
  const upstream = net.connect(Number(target.origin.port || 80), target.origin.hostname, () => {
    const headers = {
      ...req.headers,
      host: target.origin.host,
      'x-forwarded-host': req.headers.host || '',
      'x-forwarded-proto': 'https',
    };

    upstream.write(`${req.method} ${target.path} HTTP/${req.httpVersion}\r\n`);
    Object.entries(headers).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach((item) => upstream.write(`${key}: ${item}\r\n`));
      } else if (value !== undefined) {
        upstream.write(`${key}: ${value}\r\n`);
      }
    });
    upstream.write('\r\n');

    if (head.length > 0) {
      upstream.write(head);
    }

    upstream.pipe(socket);
    socket.pipe(upstream);
  });

  upstream.on('error', () => {
    socket.destroy();
  });
}

const server = https.createServer(
  {
    cert: fs.readFileSync(certPath),
    key: fs.readFileSync(keyPath),
  },
  proxyHttpRequest
);

server.on('upgrade', proxyUpgrade);
server.listen(listenPort, listenHost, () => {
  console.log(`MIMU HTTPS LAN gateway listening on https://${listenHost}:${listenPort}`);
  console.log(`frontend -> ${frontendOrigin.href}`);
  console.log(`api /api -> ${backendOrigin.href}`);
});
