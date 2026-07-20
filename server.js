const express = require('express');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://127.0.0.1:8000';

// Parse JSON and URL-encoded bodies (for other routes if needed)
app.use(express.json());

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

// Simple proxy logic using native fetch (Node.js 18+)
app.all('/api/*', async (req, res) => {
  const targetPath = req.params[0] || '';
  const url = `${FASTAPI_URL}/${targetPath}`;

  const fetchOptions = {
    method: req.method,
    headers: {},
  };

  // Forward select headers, but ignore Host to avoid routing issues
  for (const [key, value] of Object.entries(req.headers)) {
    if (key.toLowerCase() !== 'host') {
      fetchOptions.headers[key] = value;
    }
  }

  // Forward body if present
  if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
    // If it's multipart (file upload), we need to forward it as a raw stream
    if (req.headers['content-type'] && req.headers['content-type'].includes('multipart/form-data')) {
      // For multipart form uploads, we can use express middleware or forward the raw buffer/stream.
      // A simple way to handle this in Express is to read the raw request stream.
      fetchOptions.body = req; 
      // Duplex is required for streaming bodies in Node.js fetch
      fetchOptions.duplex = 'half';
    } else {
      fetchOptions.body = JSON.stringify(req.body);
    }
  }

  try {
    const response = await fetch(url, fetchOptions);
    
    // Set response headers
    res.status(response.status);
    response.headers.forEach((value, key) => {
      res.setHeader(key, value);
    });

    // Send the response body
    const bodyReader = response.body;
    if (bodyReader) {
      const nodeStream = require('stream').Readable.fromWeb(bodyReader);
      nodeStream.pipe(res);
    } else {
      res.end();
    }
  } catch (error) {
    console.error(`[Proxy Error] Failed to proxy to ${url}:`, error);
    res.status(502).json({ error: 'Failed to communicate with backend API' });
  }
});

// For SPA routing, serve index.html for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`[Frontend] Server running at http://localhost:${PORT}`);
  console.log(`[Frontend] Proxying /api/* requests to: ${FASTAPI_URL}`);
});
