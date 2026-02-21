# RUNNING.md — Starting and Verifying VerifyWise Locally

> This document covers **local (non-Docker) startup** of the VerifyWise stack using npm/Node.js
> directly, and the full **verification/validation workflow** to run against the live stack.
> For Docker-based startup see SKILLS.md § Docker Compose.

---

## Quick Reference

| What | Command |
|------|---------|
| Start everything (local) | `./scripts/start-verifywise-local.sh` |
| Stop everything (local) | `./scripts/stop-verifywise-local.sh` |
| Verify stack is up | `./scripts/verify-verifywise.sh` |
| Run showboat proof | `showboat verify demos/verification.md` |
| Browser smoke test | `rodney start && rodney open http://localhost:5173 && rodney title && rodney stop` |
| Backend URL | `http://localhost:3000` |
| Frontend URL | `http://localhost:5173` |
| Admin email | `verifywise@email.com` |
| Admin password | `MyJH4rTm!@.45L0wm` |

---

## Prerequisites

The following must be available in the environment:

| Tool | Version | Install |
|------|---------|---------|
| Node.js | ≥ 20 | `nvm install 20` |
| npm | ≥ 10 | bundled with Node.js |
| PostgreSQL | ≥ 14 | `apt install postgresql` |
| Redis | ≥ 6 | `apt install redis-server` |
| uv | any | `curl -Ls https://astral.sh/uv/install.sh \| sh` |
| Go | ≥ 1.22 | `apt install golang` |
| showboat | dev | `go install github.com/simonw/showboat@latest` |
| rodney | v0.4.0+ | `go install github.com/simonw/rodney@latest` |

---

## Part 1: Starting VerifyWise (npm-based, no Docker)

### Automated startup

The helper script handles all steps below automatically:

```bash
./scripts/start-verifywise-local.sh
```

This script:
1. Starts PostgreSQL and Redis system services
2. Creates the `verifywise` database if absent
3. Installs backend npm dependencies (`verifywise/Servers`)
4. Builds TypeScript → JavaScript (`npm run build`)
5. Runs database migrations (`npm run migrate-db`)
6. Seeds the default organization and admin user (idempotent)
7. Starts the backend server in the background (port 3000)
8. Installs frontend npm dependencies (`verifywise/Clients`)
9. Starts the Vite dev server in the background (port 5173)
10. Polls until both endpoints respond

### Manual step-by-step

If you need to run steps individually:

#### 1. System services

```bash
service postgresql start
service redis-server start

# Verify
pg_isready              # should print "accepting connections"
redis-cli ping          # should print PONG
```

#### 2. Database setup

```bash
# Create database (idempotent)
sudo -u postgres psql -c "CREATE DATABASE verifywise OWNER postgres;" 2>/dev/null || true
```

#### 3. Backend .env

The file `verifywise/Servers/.env` must exist. If missing, create it:

```bash
cp verifywise/.env.dev verifywise/Servers/.env
# Then edit REDIS_HOST: change 'redis' → 'localhost'
sed -i 's/REDIS_HOST=redis/REDIS_HOST=localhost/' verifywise/Servers/.env
```

Key values used:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=verifywise
DB_USER=postgres
DB_PASSWORD=test
REDIS_HOST=localhost
REDIS_PORT=6379
BACKEND_PORT=3000
```

#### 4. Build and migrate backend

```bash
cd verifywise/Servers
npm install
npm run build        # tsc → dist/
npm run migrate-db   # sequelize db:migrate
```

#### 5. Seed database

The `resetDatabase.ts` script has a known issue: it drops all tables before
creating the organization the admin user depends on. Use the idempotent seed
instead:

```bash
node -e "
const bcrypt = require('./verifywise/Servers/node_modules/bcrypt');
bcrypt.hash('MyJH4rTm!@.45L0wm', 10).then(hash => {
  const { Client } = require('pg');
  const db = new Client({ host:'localhost', port:5432, database:'verifywise',
                           user:'postgres', password:'test' });
  db.connect().then(async () => {
    await db.query(\`
      INSERT INTO organizations (name, onboarding_status, created_at, updated_at)
      VALUES ('VerifyWise', 'completed', NOW(), NOW())
      ON CONFLICT DO NOTHING;\`);
    await db.query(\`
      INSERT INTO users (name, surname, email, password_hash, role_id,
                         created_at, last_login, is_demo, organization_id)
      SELECT 'VerifyWise','Admin','verifywise@email.com','\${hash}',1,NOW(),NOW(),false,1
      WHERE NOT EXISTS (SELECT 1 FROM users WHERE email='verifywise@email.com');\`);
    await db.end();
    console.log('Seed done');
  });
});
" 2>&1
```

The seed script (`scripts/seed-verifywise.js`) wraps this more cleanly — see below.

#### 6. Start backend

```bash
node verifywise/Servers/dist/index.js > /tmp/verifywise-backend.log 2>&1 &
echo "Backend PID: $!"
```

#### 7. Start frontend

```bash
cd verifywise/Clients
npm install
npm run dev:vite -- --port 5173 > /tmp/verifywise-frontend.log 2>&1 &
echo "Frontend PID: $!"
```

#### 8. Wait for readiness

```bash
./scripts/wait-for-verifywise.sh    # polls http://localhost:3000/api/users/check-user-exists
```

---

## Part 2: Verification & Validation Workflow

Run these checks whenever instructed to "verify the stack" or after making changes.

### Step 1 — Backend API health

```bash
# Login and get a token
TOKEN=$(curl -s -X POST http://localhost:3000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"verifywise@email.com","password":"MyJH4rTm!@.45L0wm"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['token'])")

echo "Token: ${TOKEN:0:40}..."

# List projects (authenticated)
curl -s http://localhost:3000/api/projects \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -20
```

### Step 2 — Frontend reachability

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/
# Expect: 200
```

### Step 3 — Showboat proof-of-work

Re-execute every block in the verification doc and confirm outputs match:

```bash
export PATH=$PATH:~/go/bin
showboat verify demos/verification.md
# Exit 0 means all outputs match
```

### Step 4 — Rodney browser smoke test

```bash
export PATH=$PATH:~/go/bin
rodney start --global
rodney --global open http://localhost:5173/
rodney --global title        # → VerifyWise - Open Source AI Governance Platform
rodney --global url          # → http://localhost:5173/login
rodney --global screenshot /tmp/vw-smoke.png
rodney --global stop
```

### Step 5 — Full UI login verification

```bash
export PATH=$PATH:~/go/bin
rodney start --global
rodney --global open http://localhost:5173/
rodney --global wait "input[type=email]"
rodney --global input "input[type=email]" "verifywise@email.com"
rodney --global input "input[type=password]" 'MyJH4rTm!@.45L0wm'
rodney --global click "button[type=submit]"
rodney --global sleep 2
rodney --global url           # → http://localhost:5173/ (dashboard root)
rodney --global screenshot /tmp/vw-dashboard.png
rodney --global stop
```

### Step 6 — MCP server Python checks

```bash
# Dependencies importable
uv run python -c "import mcp, httpx, pydantic; print('OK')"

# Unit tests pass
uv run pytest tests/unit/ -v --tb=short

# Linter clean
uvx ruff check .

# Type check
uv run pyright src/
```

### Full verification script

All steps above are wrapped in:

```bash
./scripts/verify-verifywise.sh
```

---

## Part 3: Claude Code Web Environment Setup

> How to configure environment variables and initialise the environment in
> Claude Code on the web, taking advantage of the container env cache.

### How caching works

According to the [official docs](https://code.claude.com/docs/en/claude-code-on-the-web),
**custom container snapshots are not yet supported**. The `SessionStart` hook
runs on every session (including resumes). However:

> The container filesystem IS persisted and cached between sessions in the same
> environment. `node_modules`, `.venv`, built `dist/`, and Go binaries all
> survive session restarts — only **running processes** and **`/tmp`** are reset.

This means the hook should be written to **check before doing** — skip steps
that are already done, only redo what's truly stateless (starting server processes).

| Thing | Cached across sessions? | How to detect |
|-------|------------------------|---------------|
| `verifywise/Servers/node_modules` | ✅ Yes | `[ -d node_modules ]` |
| `verifywise/Clients/node_modules` | ✅ Yes (but check rollup) | validate native module |
| `verifywise/Servers/dist/` | ✅ Yes | compare mtime vs `.ts` sources |
| `.venv/` (Python) | ✅ Yes | `uv sync` is a no-op when current |
| `~/go/bin/showboat`, `rodney` | ✅ Yes | `command -v showboat` |
| PostgreSQL data + migrations | ✅ Yes | migrate-db is instant if up-to-date |
| Backend process (`node dist/`) | ❌ No — must restart | always restart |
| Frontend process (`vite`) | ❌ No — must restart | always restart |
| `/tmp/` files | ❌ No | always recreated |

**Typical warm-container hook time: ~15s** (services start + backend launch)
vs. ~3–5 min cold (full install + build).

### Warm vs cold session timing

```
COLD session (first time / cache cleared):
  Phase 2  services        ~10s
  Phase 3  uv sync         ~30s   (downloads packages)
  Phase 4  go install x2   ~60s   (compiles binaries)
  Phase 5  DB setup        ~5s
  Phase 6  npm install     ~90s   (downloads 500+ packages)
  Phase 7  tsc build       ~30s
  Phase 8  migrations      ~10s
  Phase 9  seed            ~2s
  Phase 10 backend start   ~10s
  Phase 11 npm install     ~60s
  Phase 12 frontend start  ~5s
  Total:                   ~5 min

WARM session (cached node_modules, dist/, binaries):
  Phase 2  services        ~5s    (fast when already stopped cleanly)
  Phase 3  uv sync         ~2s    (no-op)
  Phase 4  SKIP go tools   ~0s
  Phase 5  SKIP .env       ~0s
  Phase 6  SKIP npm install~0s
  Phase 7  SKIP tsc build  ~0s
  Phase 8  migrations      ~3s    (instant, nothing to run)
  Phase 9  seed            ~1s    (instant, user exists)
  Phase 10 backend start   ~5s
  Phase 11 SKIP npm install~0s
  Phase 12 frontend start  ~3s
  Total:                   ~20s
```

### Environment variables

The MCP server reads from a `.env` file (see `.env.example`). For web sessions,
write them via `$CLAUDE_ENV_FILE` in the hook so they don't need a `.env`:

```bash
# In .claude/hooks/session-start.sh
cat >> "$CLAUDE_ENV_FILE" << 'ENV'
export VERIFYWISE_BASE_URL=http://localhost:3000
export VERIFYWISE_EMAIL=verifywise@email.com
export PATH=$PATH:$HOME/go/bin
ENV
```

**Sensitive values** (passwords, API keys) should be set as **Repository
Secrets** in the Claude Code web project settings — they are injected as
env vars at session start and can be referenced as `$VERIFYWISE_PASSWORD`.

### SessionStart hook

The hook at `.claude/hooks/session-start.sh` runs on every session start.
It uses idempotency guards to skip any work the cached container already has.

| Phase | What it does | Cached? |
|-------|-------------|---------|
| 1. Guard | Exit if not `CLAUDE_CODE_REMOTE=true` | — |
| 2. System services | `service postgresql/redis start` | ❌ always |
| 3. Python deps | `uv sync` (no-op when `.venv` is current) | ✅ fast |
| 4. Go tools | `go install` only if binary missing | ✅ skip |
| 5. DB + .env | Create DB / .env only if absent | ✅ skip |
| 6. Backend npm | `npm install` only if `node_modules` missing | ✅ skip |
| 7. Backend build | `tsc` only if `dist/` older than `.ts` sources | ✅ skip |
| 8. Migrations | `sequelize migrate` (instant when up-to-date) | ✅ fast |
| 9. DB seed | Insert org + admin if absent (idempotent) | ✅ fast |
| 10. Backend start | `nohup node dist/index.js &` | ❌ always |
| 11. Frontend npm | `npm install` only if `node_modules` missing | ✅ skip |
| 12. Frontend start | `nohup npm run dev:vite &` | ❌ always |
| 13. Env vars | Write `VERIFYWISE_*` to `$CLAUDE_ENV_FILE` | ❌ always |
| 14. Health wait | Poll backend until ready | ❌ always |

### Registering the hook

The hook is registered in `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/session-start.sh"
          }
        ]
      }
    ]
  }
}
```

### Testing the hook locally

```bash
CLAUDE_CODE_REMOTE=true \
CLAUDE_PROJECT_DIR=$(pwd) \
CLAUDE_ENV_FILE=/tmp/claude-env-test.sh \
  ./.claude/hooks/session-start.sh

# Inspect what env vars were exported
cat /tmp/claude-env-test.sh
```

### Setting environment variables in Claude Code web

Go to your project's **Environment settings** in Claude Code on the web:

1. Open the environment selector → click the settings ⚙ icon
2. Add key-value pairs under **Environment Variables** (`.env` format):
   ```
   VERIFYWISE_BASE_URL=http://localhost:3000
   VERIFYWISE_EMAIL=verifywise@email.com
   ```
3. For secrets (passwords, API keys), these are injected at session start
   and available as `$VARIABLE_NAME` inside the hook and all tool calls

> Note: env vars set in the UI are available **before** the hook runs, so
> `$VERIFYWISE_PASSWORD` is readable inside `session-start.sh` directly.

---

## Stopping VerifyWise

```bash
./scripts/stop-verifywise-local.sh
```

Or manually:

```bash
pkill -f "node.*dist/index.js" || true
pkill -f "vite.*5173" || true
# PostgreSQL and Redis are system services — leave running or:
# service postgresql stop
# service redis-server stop
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `password authentication failed` | postgres password not set | `sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'test';"` |
| `Cannot connect to Redis` | Redis not started or wrong host | Check `REDIS_HOST=localhost` in `Servers/.env` |
| `Cannot find module @rollup/rollup-linux-x64-gnu` | npm optional deps bug | `rm -rf node_modules && npm install` in `Clients/` |
| Backend starts but login fails | Admin user not seeded | Run `scripts/seed-verifywise.js` |
| `resetDatabase.js` fails with FK error | Drops org before creating it | Use `seed-verifywise.js` instead |
| Showboat verify fails with PID mismatch | PID in output differs | Use `sed 's/ (PID [0-9]*)//'` in the exec block |
