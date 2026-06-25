# Deployment Plan — Zomato AI Recommender

> **Stack**: FastAPI backend → **Railway** | Vanilla HTML/JS frontend → **Vercel**

---

## Architecture Overview

```
Browser
  │
  ├─► Vercel (Static Frontend)
  │     src/ui/frontend/index.html
  │     src/ui/frontend/js/
  │     src/ui/frontend/css/
  │     Reads window.RAILWAY_API_URL to locate backend
  │
  └─► Railway (FastAPI Backend)
        uvicorn src.api.main:app
        Downloads & caches Zomato dataset from HuggingFace on first boot
        Calls Groq LLM for recommendation ranking
```

---

## Pre-Deployment Checklist

- [ ] Push all changes to GitHub (`main` branch is the deployment branch)
- [ ] Ensure `.env` is in `.gitignore` (it is ✅)
- [ ] Ensure `data/*.parquet` is in `.gitignore` (it is ✅)
- [ ] Confirm `railway.toml` and `vercel.json` are committed to the repo

---

## Part 1 — Backend on Railway

### 1.1 Create a Railway Project

1. Go to [railway.app](https://railway.app) and log in (GitHub login recommended).
2. Click **New Project → Deploy from GitHub repo**.
3. Select the `varshithakantayapalam01-sudo/Zomato-AI-Recommender` repository.
4. Railway will auto-detect `railway.toml` and use it.

### 1.2 Confirm `railway.toml` Settings

The existing [`railway.toml`](file:///d:/Cursor_projects/railway.toml) is already correct:

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn src.api.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 60
restartPolicyType = "on_failure"
```

> **Note**: Nixpacks will detect `requirements.txt` and install all Python dependencies automatically.

### 1.3 Set Environment Variables in Railway Dashboard

Navigate to your service → **Variables** tab and add the following:

| Variable | Value | Notes |
|---|---|---|
| `GROQ_API_KEY` | `gsk_...` | Your Groq API key — **required** |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Or another Groq model |
| `GROQ_TEMPERATURE` | `0.3` | LLM temperature |
| `HF_DATASET_NAME` | `ManikaSaini/zomato-restaurant-recommendation` | HuggingFace dataset |
| `DATA_CACHE_PATH` | `data/restaurants.parquet` | Local cache path inside container |
| `BUDGET_THRESHOLDS_LOW_MAX` | `500` | Budget tier cutoff (INR) |
| `BUDGET_THRESHOLDS_MEDIUM_MAX` | `1500` | Budget tier cutoff (INR) |
| `MAX_CANDIDATES_FOR_LLM` | `20` | Candidate pool size |
| `TOP_K_RECOMMENDATIONS` | `5` | Number of results returned |

> **Tip**: You can copy these from your local [`.env.example`](file:///d:/Cursor_projects/.env.example) file.

### 1.4 Deploy & Note Your Public URL

1. Railway will trigger a deployment automatically after you connect the repo.
2. Once deployed (green status), go to **Settings → Networking → Generate Domain**.
3. Your backend public URL will look like:
   ```
   https://zomato-ai-recommender-production.up.railway.app
   ```
4. **Save this URL** — you will need it for the Vercel step.

### 1.5 Verify the Backend

Run these smoke tests against your Railway URL:

```bash
# Health check
curl https://<your-railway-url>/api/v1/health

# Locations endpoint
curl https://<your-railway-url>/api/v1/locations

# Cuisines endpoint
curl https://<your-railway-url>/api/v1/cuisines
```

Expected: `200 OK` responses with JSON data.

> ⚠️ **First-boot warning**: On first deployment, Railway downloads and caches the HuggingFace dataset (`~50–200 MB`). The health check may take up to **60 seconds** to pass. This is normal.

---

## Part 2 — Frontend on Vercel

### 2.1 Create a Vercel Project

1. Go to [vercel.com](https://vercel.com) and log in (GitHub login recommended).
2. Click **Add New → Project**.
3. Import the `varshithakantayapalam01-sudo/Zomato-AI-Recommender` repository.
4. Vercel will auto-detect `vercel.json` in the root.

### 2.2 Confirm `vercel.json` Settings

The existing [`vercel.json`](file:///d:/Cursor_projects/vercel.json) is already correct:

```json
{
  "version": 2,
  "buildCommand": "echo window.RAILWAY_API_URL = '\"$RAILWAY_API_URL\"'; > src/ui/frontend/config.js",
  "outputDirectory": "src/ui/frontend",
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/index.html"
    }
  ]
}
```

> **How it works**: The build command injects your Railway backend URL into `config.js` at build time. The frontend's `app.js` reads `window.RAILWAY_API_URL` at runtime to know where to send API requests.

### 2.3 Set Environment Variable in Vercel Dashboard

Navigate to your project → **Settings → Environment Variables** and add:

| Variable | Value | Environment |
|---|---|---|
| `RAILWAY_API_URL` | `https://<your-railway-url>` | Production, Preview, Development |

Replace `<your-railway-url>` with the URL you saved in Step 1.4.

> **Important**: Do **not** include a trailing slash in the URL.

### 2.4 Update CORS in the Backend

The FastAPI app already has your Vercel domain pre-configured in [`src/api/main.py`](file:///d:/Cursor_projects/src/api/main.py):

```python
allow_origins=[
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Production Vercel deployment
    "https://zomato-ai-recommender.vercel.app",
    # Vercel preview deployments (branch/PR deploys)
    "https://zomato-ai-recommender-git-main-varshithakantayapalam01-sudos.vercel.app",
]
```

✅ If your Vercel project URL matches `zomato-ai-recommender.vercel.app`, no changes needed.  
⚠️ If Vercel assigns a different domain, update the `allow_origins` list and redeploy Railway.

### 2.5 Trigger a Deployment

1. Click **Deploy** in the Vercel dashboard (or push to `main` to auto-deploy).
2. Wait for the build to complete — the build command rewrites `config.js`.
3. Your frontend will be live at:
   ```
   https://zomato-ai-recommender.vercel.app
   ```

### 2.6 Verify the Frontend

1. Open `https://zomato-ai-recommender.vercel.app` in a browser.
2. Open browser DevTools → **Network** tab.
3. Perform a restaurant search and confirm API calls go to your Railway URL.
4. Confirm recommendations are returned successfully.

---

## Part 3 — Post-Deployment

### 3.1 Custom Domains (Optional)

| Service | Steps |
|---|---|
| **Railway** | Settings → Networking → Custom Domain → add your domain + configure DNS CNAME |
| **Vercel** | Settings → Domains → Add → configure DNS as instructed by Vercel |

If you add a custom domain to Vercel, also add it to the `allow_origins` list in [`src/api/main.py`](file:///d:/Cursor_projects/src/api/main.py) and redeploy Railway.

### 3.2 Automatic Deployments (CI/CD)

Both platforms auto-deploy on every push to `main` by default:

- **Railway**: Rebuilds the Docker/Nixpacks image and restarts the service.
- **Vercel**: Rebuilds static assets (re-running the build command, re-injecting `RAILWAY_API_URL`).

### 3.3 Monitoring & Logs

| Service | Where to find logs |
|---|---|
| **Railway** | Project → Service → **Logs** tab (real-time streaming) |
| **Vercel** | Project → **Deployments** → click a deployment → **Functions** log |

### 3.4 Dataset Cache Note

The Parquet cache (`data/restaurants.parquet`) lives inside the Railway container filesystem. It is re-downloaded from HuggingFace on **every new deployment** (ephemeral container). This is expected behavior and takes ~30–60 seconds during cold start. If you want persistent caching across deploys, consider attaching a **Railway Volume** (`/data`) to the service.

---

## Summary

| Step | Platform | Action |
|---|---|---|
| 1 | Railway | Connect GitHub repo, confirm `railway.toml` |
| 2 | Railway | Set all env variables from `.env.example` |
| 3 | Railway | Deploy, generate public domain, verify `/api/v1/health` |
| 4 | Vercel | Connect GitHub repo, confirm `vercel.json` |
| 5 | Vercel | Set `RAILWAY_API_URL` env variable |
| 6 | Vercel | Deploy, verify frontend loads and calls backend |
| 7 | Both | (Optional) Add custom domains, update CORS list |
