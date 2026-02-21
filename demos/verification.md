# VerifyWise Local Setup Verification

*2026-02-21T07:43:51Z by Showboat dev*
<!-- showboat-id: 993e948b-15c0-41bb-9b37-d40b5bf57717 -->

## Tool Verification

Verifying showboat and rodney CLI tools are installed and functional.

```bash
showboat --version
```

```output
dev
```

```bash
rodney --version
```

```output
dev
```

## VerifyWise Backend (Node.js/npm)

Backend started with: npm run build && node dist/index.js
Running at http://localhost:3000

```bash
curl -s -X POST http://localhost:3000/api/users/login -H 'Content-Type: application/json' -d @/tmp/login.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('Login:', d['message'], '| Token:', d['data']['token'][:40]+'...')"
```

```output
Login: Accepted | Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ...
```

## VerifyWise Frontend (Vite/React)

Frontend started with: npm run dev:vite
Running at http://localhost:5173

```bash
curl -s http://localhost:5173/ | head -3
```

```output
<!DOCTYPE html>
<html lang="en">
  <head>
```

## Browser Automation with Rodney

End-to-end verification: start Chrome, navigate to frontend, confirm page title and URL.

```bash

export PATH=$PATH:~/go/bin
rodney start --global 2>&1 | grep 'Chrome started' | sed 's/ (PID [0-9]*)//'
rodney --global open http://localhost:5173/ 2>&1
rodney --global title 2>&1
rodney --global url 2>&1
rodney --global stop 2>&1 | grep Chrome

```

```output
Chrome started
VerifyWise - Open Source AI Governance Platform
VerifyWise - Open Source AI Governance Platform
http://localhost:5173/login
Chrome stopped
```

## MCP Server Dependencies (Python/uv)

```bash
cd /home/user/verifywise-mcp && uv run python -c 'import mcp, httpx, pydantic; print("mcp OK, httpx", httpx.__version__, "pydantic", pydantic.__version__)'
```

```output
mcp OK, httpx 0.28.1 pydantic 2.12.5
```
