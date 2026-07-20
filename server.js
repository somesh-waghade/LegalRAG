const express = require('express');
const path = require('path');
const http = require('http');
const https = require('https');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://127.0.0.1:8000';

// Serve static assets from the public directory
app.use(express.static(path.join(__dirname, 'public')));

// Spawn the FastAPI backend as a child process if targeting localhost/127.0.0.1
if (FASTAPI_URL.includes('127.0.0.1') || FASTAPI_URL.includes('localhost')) {
  const { spawn } = require('child_process');
  console.log('[Frontend] Spawning FastAPI backend subprocess...');
  
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const backend = spawn(pythonCmd, [
    '-m', 'uvicorn', 'backend.api:app',
    '--host', '127.0.0.1',
    '--port', '8000',
    '--log-level', 'info'
  ], {
    cwd: __dirname
  });

  backend.stdout.on('data', (data) => {
    process.stdout.write(`[Backend] ${data}`);
  });

  backend.stderr.on('data', (data) => {
    process.stderr.write(`[Backend ERROR] ${data}`);
  });

  backend.on('close', (code) => {
    console.log(`[Backend] Process exited with code ${code}`);
  });
}

// Stream proxy for API requests. This avoids buffering multipart uploads and
// works consistently across Node versions used by Render.
app.all('/api/*', async (req, res) => {
  const targetPath = req.params[0] || '';
  const targetUrl = new URL(`${FASTAPI_URL}/${targetPath}`);
  targetUrl.search = req.url.includes('?') ? req.url.slice(req.url.indexOf('?')) : '';

  const headers = { ...req.headers };
  delete headers.host;

  const options = {
    method: req.method,
    hostname: targetUrl.hostname,
    port: targetUrl.port || (targetUrl.protocol === 'https:' ? 443 : 80),
    path: `${targetUrl.pathname}${targetUrl.search}`,
    headers,
  };

  const transport = targetUrl.protocol === 'https:' ? https : http;

  const proxyReq = transport.request(options, (proxyRes) => {
    res.status(proxyRes.statusCode || 502);
    Object.entries(proxyRes.headers).forEach(([key, value]) => {
      if (value !== undefined) {
        res.setHeader(key, value);
      }
    });
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (error) => {
    console.error(`[Proxy Error] Failed to proxy to ${targetUrl.toString()}:`, error);
    if (res.headersSent) {
      res.end();
      return;
    }
    res.status(502).json({ error: 'Failed to communicate with backend API' });
  });

  req.pipe(proxyReq);
});

// For SPA routing, serve index.html for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`[Frontend] Server running at http://localhost:${PORT}`);
  console.log(`[Frontend] Proxying /api/* requests to: ${FASTAPI_URL}`);
});
