#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Capstone Deploy Script
# "CI/CD-lite" for a capstone project
#
# Usage:
#   ./deploy.sh                    # deploy latest main branch
#   ./deploy.sh --branch feat/xyz  # deploy a specific branch
#
# What it does (runs ON the Oracle VM via SSH):
#   1. Pull latest code from git
#   2. Rebuild the Docker image (only layers that changed)
#   3. Run Alembic migrations (in a temp container, before the app restarts)
#   4. Rolling restart of the web service (zero-downtime via depends_on health)
#   5. Print logs
#
# How to use from your laptop:
#   ssh ubuntu@YOUR_VM_IP 'bash -s' < deploy.sh
# OR
#   ssh ubuntu@YOUR_VM_IP "cd ~/capstron && ./deploy.sh"
# =============================================================================

set -euo pipefail      # exit on error, unbound variable, or pipe failure

REPO_DIR="$HOME/capstron"
COMPOSE_FILE="$REPO_DIR/docker-compose.yml"
ENV_FILE="$REPO_DIR/backend/.env.production"
BRANCH="${1:-main}"

# Allow --branch flag
if [[ "${1:-}" == "--branch" ]]; then
    BRANCH="${2:-main}"
fi

echo "=============================================="
echo "  Capstron Deploy — branch: $BRANCH"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

# ── Step 1: Pull latest code ───────────────────────────────────────────────
echo ""
echo "[1/5] Pulling latest code..."
cd "$REPO_DIR"
git fetch --all
git checkout "$BRANCH"
git pull origin "$BRANCH"
echo "      ✅ Code updated to $(git rev-parse --short HEAD)"

# ── Step 2: Verify secrets file exists ────────────────────────────────────
echo ""
echo "[2/5] Checking secrets..."
if [[ ! -f "$ENV_FILE" ]]; then
    echo "      ❌ ERROR: $ENV_FILE not found!"
    echo "      Copy .env.production.example → .env.production and fill in secrets."
    exit 1
fi
echo "      ✅ Secrets file present"

# ── Step 3: Build images ───────────────────────────────────────────────────
echo ""
echo "[3/5] Building Docker images (only changed layers)..."
docker compose -f "$COMPOSE_FILE" build --parallel
echo "      ✅ Images built"

# ── Step 4: Run database migrations ───────────────────────────────────────
echo ""
echo "[4/5] Running Alembic migrations..."
# Start DB service only (if not already running), then run migrations in a
# temporary container that mounts the same backend code.
docker compose -f "$COMPOSE_FILE" up -d db
sleep 3   # brief pause for Postgres to be ready

docker compose -f "$COMPOSE_FILE" run --rm \
    -e POSTGRES_HOST=db \
    --env-file "$ENV_FILE" \
    web \
    python -m alembic upgrade head

echo "      ✅ Migrations complete"

# ── Step 5: Rolling restart ────────────────────────────────────────────────
echo ""
echo "[5/5] Starting / restarting all services..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
echo "      ✅ Services started"

# ── Summary ───────────────────────────────────────────────────────────────
echo ""
echo "=============================================="
echo "  Deploy complete!"
echo "=============================================="
echo ""
echo "  Service status:"
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "  Health check:"
sleep 5
curl -sf http://localhost/health && echo "  ✅ /health → OK" || echo "  ⚠️  /health not responding yet (models still loading)"

echo ""
echo "  Tail logs with:"
echo "    docker compose -f $COMPOSE_FILE logs -f web"
