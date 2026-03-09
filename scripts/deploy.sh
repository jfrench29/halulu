#!/bin/bash
set -euo pipefail

# ============================================================
# Halulu Deployment Script
# Run this in a terminal that supports browser popups (for railway login)
# ============================================================

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
echo "==> Working directory: $PROJECT_DIR"

# ── Step 1: Railway Login ──────────────────────────────────
echo ""
echo "==> Step 1: Railway Login"
echo "    (This will open your browser)"
railway login
echo "    Logged in as: $(railway whoami)"

# ── Step 2: Create Railway Project ─────────────────────────
echo ""
echo "==> Step 2: Creating Railway project..."
railway init --name halulu 2>/dev/null || echo "    (Project may already exist, continuing...)"

# ── Step 3: Link to GitHub ─────────────────────────────────
echo ""
echo "==> Step 3: Linking to GitHub repo..."
echo "    NOTE: If this doesn't auto-link, go to Railway dashboard and"
echo "    connect the 'jfrench29/halulu' GitHub repo manually."
railway link 2>/dev/null || true

# ── Step 4: Add PostgreSQL ─────────────────────────────────
echo ""
echo "==> Step 4: Adding PostgreSQL..."
echo "    Go to your Railway dashboard: https://railway.com/dashboard"
echo "    Open the 'halulu' project → click '+ New' → 'Database' → 'Add PostgreSQL'"
echo ""
echo "    Railway will auto-set DATABASE_URL on your app service."
echo ""
read -p "    Press Enter after you've added PostgreSQL..."

# ── Step 5: Verify DATABASE_URL ────────────────────────────
echo ""
echo "==> Step 5: Verifying DATABASE_URL..."
if railway variables 2>/dev/null | grep -q DATABASE_URL; then
    echo "    DATABASE_URL is set."
else
    echo "    WARNING: DATABASE_URL not found. Make sure PostgreSQL is linked"
    echo "    to your web service in Railway dashboard."
fi

# ── Step 6: Set API Keys ──────────────────────────────────
echo ""
echo "==> Step 6: Setting environment variables..."

# Prompt for API keys
read -p "    Enter your OPENAI_API_KEY (or press Enter to skip): " OPENAI_KEY
if [ -n "$OPENAI_KEY" ]; then
    railway variables set OPENAI_API_KEY="$OPENAI_KEY"
    echo "    Set OPENAI_API_KEY"
fi

read -p "    Enter your ANTHROPIC_API_KEY (or press Enter to skip): " ANTHROPIC_KEY
if [ -n "$ANTHROPIC_KEY" ]; then
    railway variables set ANTHROPIC_API_KEY="$ANTHROPIC_KEY"
    echo "    Set ANTHROPIC_API_KEY"
fi

read -p "    Enter your GOOGLE_API_KEY (or press Enter to skip): " GOOGLE_KEY
if [ -n "$GOOGLE_KEY" ]; then
    railway variables set GOOGLE_API_KEY="$GOOGLE_KEY"
    echo "    Set GOOGLE_API_KEY"
fi

read -p "    Enter your XAI_API_KEY (or press Enter to skip): " XAI_KEY
if [ -n "$XAI_KEY" ]; then
    railway variables set XAI_API_KEY="$XAI_KEY"
    echo "    Set XAI_API_KEY"
fi

read -p "    Enter your MISTRAL_API_KEY (or press Enter to skip): " MISTRAL_KEY
if [ -n "$MISTRAL_KEY" ]; then
    railway variables set MISTRAL_API_KEY="$MISTRAL_KEY"
    echo "    Set MISTRAL_API_KEY"
fi

read -p "    Enter your TOGETHER_API_KEY (or press Enter to skip): " TOGETHER_KEY
if [ -n "$TOGETHER_KEY" ]; then
    railway variables set TOGETHER_API_KEY="$TOGETHER_KEY"
    echo "    Set TOGETHER_API_KEY"
fi

# Analytics (disabled by default — enable after Plausible setup)
railway variables set PLAUSIBLE_ENABLED="false" 2>/dev/null || true
railway variables set PLAUSIBLE_DOMAIN="halulu.ai" 2>/dev/null || true
echo "    Set Plausible vars (disabled until you set up Plausible)"

# ── Step 7: Deploy ─────────────────────────────────────────
echo ""
echo "==> Step 7: Deploying to Railway..."
railway up --detach
echo "    Deployment triggered. Watch logs with: railway logs"

# ── Step 8: Set up custom domain ───────────────────────────
echo ""
echo "==> Step 8: Custom Domain Setup"
echo ""
echo "    In the Railway dashboard, go to:"
echo "    Project → web service → Settings → Networking → Custom Domain"
echo ""
echo "    Add these two domains:"
echo "      1. halulu.ai"
echo "      2. www.halulu.ai"
echo ""
echo "    Railway will give you a CNAME target like:"
echo "      halulu-production-xxxx.up.railway.app"
echo ""
echo "    Copy that CNAME target for Cloudflare setup (see DEPLOY.md Step 6)."

# ── Step 9: Verify deployment ──────────────────────────────
echo ""
echo "==> Step 9: Checking deployment status..."
sleep 5
railway status 2>/dev/null || echo "    Check Railway dashboard for deployment status"

echo ""
echo "============================================================"
echo "  DEPLOYMENT COMPLETE"
echo "============================================================"
echo ""
echo "  GitHub:    https://github.com/jfrench29/halulu"
echo "  Railway:   Check your dashboard at https://railway.com"
echo ""
echo "  Next steps:"
echo "    1. Verify the app loads at your Railway URL"
echo "    2. Set up Cloudflare DNS (see DEPLOY.md Step 6)"
echo "    3. Run first evaluation:"
echo "       eval \$(railway variables --format shell)"
echo "       python -m runner.evaluate_models --models gpt-4o claude-sonnet-4-20250514"
echo "    4. Set up Plausible analytics (see DEPLOY.md Step 10)"
echo ""
