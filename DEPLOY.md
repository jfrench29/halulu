# Deploying Halulu to halulu.ai

Step-by-step guide to publish the AI Reliability Index on Railway with a
custom domain registered through Squarespace.

---

## Architecture

```
                    ┌────────────┐
                    │ Cloudflare │ CDN + DDoS + CNAME flattening
                    │  (free)    │
                    └─────┬──────┘
                          │
┌──────────────┐    ┌─────▼─────────────────────────────────┐
│  Squarespace │    │              Railway                   │
│  (registrar) │    │                                       │
│  halulu.ai   │    │  ┌─────────────┐   ┌──────────────┐  │
└──────────────┘    │  │  Streamlit  │──▶│  PostgreSQL   │  │
                    │  │  + health   │   │  (conn pool)  │  │
┌──────────────┐    │  └─────────────┘   └──────────────┘  │
│   GitHub     │───▶│   auto-deploy                        │
│   (repo)     │    │                                       │
└──────────────┘    │  ┌─────────────┐                      │
                    │  │ eval-runner │  (cron, weekly)       │
┌──────────────┐    │  └─────────────┘                      │
│  Plausible   │    └───────────────────────────────────────┘
│  (analytics) │
└──────────────┘
```

**Stack decisions:**

| Layer        | Choice                 | Why                                      |
|--------------|------------------------|------------------------------------------|
| Hosting      | Railway                | Already using it. Auto-deploy, SSL, cron |
| Database     | Railway PostgreSQL     | Persistent, concurrent-safe, conn pooled |
| CDN/Security | Cloudflare (free)      | DDoS, CNAME flattening, cache, WAF       |
| DNS          | Cloudflare             | Apex domain support via CNAME flattening |
| Registrar    | Squarespace            | Already own it. Keeps renewal there      |
| CI/CD        | GitHub → Railway       | Push to main = auto-deploy               |
| Analytics    | Plausible              | Privacy-friendly, no cookies, GDPR-free  |
| Monitoring   | Railway logs + health  | Built-in health check on :8081/health    |

---

## Step 1 — Initialize Git & Push to GitHub

```bash
cd ai_reliability_index

git init
git add .
git commit -m "Initial commit: AI Reliability Index"

# Private repo (make public when ready)
gh repo create halulu --private --source=. --push
```

---

## Step 2 — Create Railway Project

```bash
railway login
railway init
# Name it "halulu" when prompted
```

Or via dashboard: https://railway.com/dashboard → **New Project** →
**Deploy from GitHub Repo** → select `halulu`.

---

## Step 3 — Add PostgreSQL

```bash
railway add --plugin postgresql
```

Or dashboard: **+ New** → **Database** → **Add PostgreSQL**.

Verify `DATABASE_URL` is set:

```bash
railway variables
```

---

## Step 4 — Set Environment Variables

```bash
# AI model API keys (for the eval runner)
railway variables set OPENAI_API_KEY="sk-..."
railway variables set ANTHROPIC_API_KEY="sk-ant-..."
railway variables set GOOGLE_API_KEY="..."

# Analytics (enable after setting up Plausible in Step 10)
railway variables set PLAUSIBLE_ENABLED="true"
railway variables set PLAUSIBLE_DOMAIN="halulu.ai"
```

**Security notes:**
- Never commit API keys to Git. `.env.example` documents what's needed.
- Railway encrypts all variables at rest.
- API keys are only used by the eval runner (cron service), never exposed
  to the public dashboard.

---

## Step 5 — Deploy

```bash
git push origin main
```

Railway auto-deploys. Watch:

```bash
railway logs
```

Nixpacks detects `requirements.txt` + `runtime.txt` (Python 3.11),
installs deps, runs Procfile (Streamlit on `$PORT`, health check on `:8081`).

---

## Step 6 — Configure Custom Domain

### 6a. Add domain in Railway

1. Railway dashboard → project → web service → **Settings** → **Networking**
2. **+ Custom Domain** → enter `halulu.ai`
3. **+ Custom Domain** → enter `www.halulu.ai`
4. Copy the **CNAME target** shown (e.g., `halulu-production-xxxx.up.railway.app`)

### 6b. DNS via Cloudflare (recommended)

Squarespace cannot CNAME the apex domain. Use Cloudflare for DNS
(Squarespace stays as registrar):

1. Create Cloudflare account → add site `halulu.ai` → free plan
2. Cloudflare gives you two nameservers
3. In Squarespace → **Domains** → **halulu.ai** → **Nameservers** →
   switch to **Custom nameservers** → enter the Cloudflare pair
4. In Cloudflare DNS, add:

   | Type  | Name  | Content                                 | Proxy |
   |-------|-------|-----------------------------------------|-------|
   | CNAME | `@`   | `halulu-production-xxxx.up.railway.app` | ON    |
   | CNAME | `www` | `halulu-production-xxxx.up.railway.app` | ON    |

5. Cloudflare → **SSL/TLS** → set to **Full (Strict)**

### 6c. Cloudflare Security Settings

1. **Security** → **WAF** → enable **Managed Ruleset** (free tier)
2. **Security** → **Bots** → enable **Bot Fight Mode**
3. **Speed** → **Optimization** → enable **Auto Minify** (JS/CSS/HTML)
4. **Caching** → **Configuration** → set browser cache TTL to 4 hours
5. **Rules** → **Page Rules** → add:
   - `halulu.ai/*` → Cache Level: Standard, Edge Cache TTL: 2 hours

### 6d. Verify

```bash
dig halulu.ai        # Should resolve
curl -I https://halulu.ai  # Should return 200
```

Railway auto-provisions SSL via Let's Encrypt.

---

## Step 7 — Run First Evaluation

```bash
# Pull Railway env vars into your local shell
eval $(railway variables --format shell)

# Run against public test set
python -m runner.evaluate_models \
  --models gpt-4o claude-sonnet-4-20250514 gemini-2.0-flash

# Or run inside Railway
railway shell
python -m runner.evaluate_models --models gpt-4o claude-sonnet-4-20250514
```

Refresh https://halulu.ai — the leaderboard populates immediately.

---

## Step 8 — Set Up Weekly Evaluations

1. Railway dashboard → **+ New** → **Empty Service** → name it `eval-runner`
2. Connect to the same GitHub repo
3. **Settings** → **Start Command**:
   ```
   python -m runner.evaluate_models --models gpt-4o claude-sonnet-4-20250514 gemini-2.0-flash --quiet
   ```
4. **Settings** → **Cron Schedule**: `0 6 * * 1` (Mondays 6:00 AM UTC)
5. Link the same environment variables (DATABASE_URL + API keys)

---

## Step 9 — Health Check Monitoring

The app runs a health check server on port 8081 alongside Streamlit.

**Test it:**
```bash
curl https://halulu.ai:8081/health
# → {"status": "ok", "results": 450}
```

**Set up uptime monitoring:**
- **UptimeRobot** (free, 5-min checks): https://uptimerobot.com
  - Add HTTP monitor → URL: `https://halulu.ai`
  - Add keyword monitor → check for "halulu" in response
  - Set up email/Slack alerts for downtime

- **Railway** has built-in health checks:
  1. Service → **Settings** → **Health Check Path** → `/health`
  2. Railway will restart the service if the health check fails

---

## Step 10 — Analytics (Plausible)

Privacy-friendly analytics. No cookies, GDPR-compliant, developer-friendly.

### Option A: Plausible Cloud ($9/month)

1. Sign up at https://plausible.io
2. Add site: `halulu.ai`
3. Done — the Streamlit app already injects the Plausible script
   when `PLAUSIBLE_ENABLED=true` (set in Step 4)

### Option B: Self-host Plausible (free)

1. Deploy Plausible Community Edition on Railway:
   https://github.com/plausible/community-edition
2. Set `PLAUSIBLE_DOMAIN` env var to your self-hosted instance

### What you'll see:

- Unique visitors, page views, bounce rate
- Traffic sources (Twitter, HN, Google, direct)
- Geographic distribution
- Device/browser breakdown
- No cookie banners needed

---

## Step 11 — Monetization Roadmap

### Phase 1: Audience Building (now)

The dashboard footer links to your GitHub. Add these as you get traction:

- **Newsletter signup** — add a Buttondown or Substack form to collect
  emails ("Get notified when new evaluations drop")
- **Twitter/X presence** — tweet weekly results with OG image cards
  (the app sets Open Graph meta tags)
- **HN / Reddit launches** — the methodology page builds credibility

### Phase 2: API Access (when you have traffic)

Add a FastAPI layer that serves:
```
GET /api/v1/leaderboard         → current rankings (free)
GET /api/v1/model/{name}/history → trend data (free tier: 30 days)
GET /api/v1/badge/{model}.svg   → embeddable reliability badge (free)
GET /api/v1/export              → full dataset export (paid)
```

Monetization options:
- **Freemium API** — free tier with rate limits, paid for bulk/historical
- **Sponsored evaluations** — companies pay to add their model
- **Embeddable badges** — "Reliability Score: 87/100" badges for model cards
  (like "build passing" on GitHub)

### Phase 3: Premium Features

- **Custom benchmark suites** — enterprises pay to run proprietary benchmarks
- **Continuous monitoring** — real-time hallucination detection for production AI
- **Consulting** — help companies evaluate AI reliability for specific use cases

---

## Security Checklist

- [x] CORS enabled (`.streamlit/config.toml`)
- [x] XSRF protection enabled
- [x] No API keys in code (env vars only)
- [x] XSS-safe rendering (untrusted content uses `st.text`, not `st.markdown`)
- [x] Database connection pooling (ThreadedConnectionPool, max 10 conns)
- [x] Connection keepalives and timeouts configured
- [x] All queries bounded with LIMIT (no unbounded SELECT *)
- [x] Batch writes (one transaction per model, not per row)
- [x] Full UUIDs for run_id (no collision risk)
- [x] Error responses not graded (separate `error=True` flag)
- [x] API calls retry with exponential backoff (tenacity)
- [x] HTTP clients reused across calls (no per-call TCP/TLS overhead)
- [x] Cloudflare WAF + Bot Fight Mode
- [x] Health check endpoint for automated monitoring
- [ ] Rate limiting on public dashboard (add via Cloudflare Page Rules if needed)
- [ ] Content Security Policy headers (add when migrating to FastAPI)

---

## Verification Checklist

- [ ] `https://halulu.ai` loads the dashboard
- [ ] SSL valid (green padlock)
- [ ] Leaderboard shows data after first eval run
- [ ] `git push origin main` triggers Railway auto-deploy
- [ ] `curl halulu.ai:8081/health` returns `{"status": "ok"}`
- [ ] Plausible shows visitor data
- [ ] Weekly cron eval runs successfully
- [ ] `www.halulu.ai` works (Cloudflare CNAME)
- [ ] Cloudflare WAF enabled
- [ ] No API keys in git history (`git log -p | grep -i "sk-"`)

---

## Cost Estimate

| Service            | Plan   | Monthly Cost |
|--------------------|--------|--------------|
| Railway (web)      | Hobby  | ~$5          |
| Railway (Postgres) | Hobby  | ~$5          |
| Railway (cron)     | Hobby  | ~$1          |
| Cloudflare         | Free   | $0           |
| Plausible          | Cloud  | $9           |
| Squarespace domain | Annual | ~$2/mo       |
| **Total**          |        | **~$22/mo**  |

To save $9/mo, self-host Plausible on Railway or use Cloudflare Analytics
(free but less detailed).

---

## Future Scaling Path

### Phase 2 — API + Static Frontend (when Streamlit is the bottleneck)

- Replace Streamlit with **FastAPI** backend + **Next.js** frontend
- Frontend on **Vercel** (free, global CDN, ISR for leaderboard pages)
- FastAPI + PostgreSQL stays on Railway
- Add Redis on Railway for response caching

### Phase 3 — Scale Evaluations

- Dedicated eval-runner service with more CPU/RAM
- Job queue (Redis + worker) for parallel model calls
- Add more models: Mistral, Llama, Qwen, Cohere, DeepSeek

### Phase 4 — Community + Revenue

- Auth via Clerk or Supabase Auth
- Community adversarial prompt submissions (Layer 4 dataset)
- Public API with rate-limited free tier + paid plans
- Embeddable reliability badges

The architecture supports all phases without re-platforming.

---

## Quick Reference

| What              | Where                                     |
|-------------------|-------------------------------------------|
| App URL           | https://halulu.ai                         |
| Health check      | https://halulu.ai:8081/health             |
| Railway dashboard | https://railway.com/project/...           |
| GitHub repo       | https://github.com/jfrench29/halulu       |
| DNS/CDN           | Cloudflare                                |
| Registrar         | Squarespace                               |
| Database          | Railway PostgreSQL                        |
| Analytics         | Plausible (halulu.ai dashboard)           |
| CI/CD             | GitHub push → Railway auto-deploy         |
| SSL               | Railway (Let's Encrypt) + Cloudflare      |
