# Gemini Motion Lab — Deployment Guide

## Live URLs

| Service | URL |
|---|---|
| Frontend | `https://gemini-motion-lab-frontend-<PROJECT_NUMBER>.<REGION>.run.app` |
| Backend | `https://gemini-motion-lab-backend-<PROJECT_NUMBER>.<REGION>.run.app` |
| Project | `<YOUR_PROJECT_ID>` |
| Region | `us-central1` |

> Cloud Run service URLs are permanent — they do not change between redeployments.

---

## Redeploying

### Backend changed

```bash
cd backend

gcloud run deploy gemini-motion-lab-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 3 \
  --memory 2Gi \
  --port 8080 \
  --project <YOUR_PROJECT_ID> \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=<YOUR_PROJECT_ID>,GOOGLE_CLOUD_LOCATION=us-central1,GCS_BUCKET=gemini-motion-lab,GCS_SIGNING_SA=gemini-motion-lab-sa@<YOUR_PROJECT_ID>.iam.gserviceaccount.com,GOOGLE_GENAI_USE_VERTEXAI=true,MOCK_AI=false,GOOGLE_WALLET_ISSUER_ID=<YOUR_WALLET_ISSUER_ID>,GOOGLE_WALLET_SA_KEY_PATH=/secrets/wallet/wallet-key.json,APPLE_PASS_TYPE_ID=<YOUR_APPLE_PASS_TYPE_ID>,APPLE_PASS_TEAM_ID=<YOUR_APPLE_TEAM_ID>,APPLE_PASS_CERT_PATH=/secrets/cert/pass_cert.pem,APPLE_PASS_KEY_PATH=/secrets/key/pass_key.pem,APPLE_WWDR_CERT_PATH=/secrets/wwdr/wwdr.pem,PUBLIC_BASE_URL=https://gemini-motion-lab-backend-<PROJECT_NUMBER>.<REGION>.run.app" \
  --set-secrets "APPLE_PASS_KEY_PASSWORD=apple-pass-key-password:latest,/secrets/cert/pass_cert.pem=apple-pass-cert:latest,/secrets/key/pass_key.pem=apple-pass-key:latest,/secrets/wwdr/wwdr.pem=apple-wwdr-cert:latest,/secrets/wallet/wallet-key.json=google-wallet-sa-key:latest"
```

Frontend does **not** need to be redeployed when only backend code changes.

---

### Frontend changed

The backend URL is hardcoded as the default `ARG` in `frontend/Dockerfile` — no extra flags needed.

```bash
cd frontend

gcloud run deploy gemini-motion-lab-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 3 \
  --port 8080 \
  --project <YOUR_PROJECT_ID>
```

> If the backend URL ever changes, update `ARG VITE_API_BASE=...` in `frontend/Dockerfile` before deploying.

---

### Both changed

Deploy backend first, then frontend. Use both commands above in order.

---

## First-time setup

### Secrets (one-time)

All 5 secrets must exist in Secret Manager before deploying the backend:

| Secret name | Contents |
|---|---|
| `apple-pass-key-password` | Apple Wallet key password |
| `apple-pass-cert` | `pass_cert.pem` |
| `apple-pass-key` | `pass_key.pem` |
| `apple-wwdr-cert` | `wwdr.pem` |
| `google-wallet-sa-key` | Google Wallet service account JSON |

### IAM (one-time)

Required for GCS signed URL generation. Run once per project:

```bash
gcloud iam service-accounts add-iam-policy-binding \
  gemini-motion-lab-sa@<YOUR_PROJECT_ID>.iam.gserviceaccount.com \
  --member="serviceAccount:<PROJECT_NUMBER>-compute@developer.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project <YOUR_PROJECT_ID>
```

---

## Checking backend logs

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=gemini-motion-lab-backend" \
  --limit=50 \
  --project <YOUR_PROJECT_ID> \
  --format="value(timestamp,textPayload)" \
  --freshness=10m
```

---

## Local development

```bash
# Terminal 1 — Backend
cd backend
pip install .
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
# Runs at http://localhost:5173, calls backend at http://localhost:8000
```

To run without real AI (no API keys needed):

```bash
# backend/.env
MOCK_AI=true
```

---

## Dockerfiles (current)

### frontend/Dockerfile

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE=https://gemini-motion-lab-backend-<PROJECT_NUMBER>.<REGION>.run.app
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
```

### backend/Dockerfile

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY app/ ./app/
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| `Upload failed: 405` | `VITE_API_BASE` wrong — frontend calling itself | Check `ARG VITE_API_BASE` in `frontend/Dockerfile`, redeploy frontend |
| `signBlob` 403 error | Missing IAM token creator role | Run the IAM command in First-time setup |
| Container OOM / crash | Memory limit too low | `--memory 2Gi` is required on backend deploy |
| CORS error in browser | Stale backend deployed without CORS fix | Redeploy backend (`main.py` has `allow_origins=["*"]`) |
| `generate-avatar` 500 | Gemini model error or GCS permission issue | Check logs with the logging command above |

---

## Showcase videos

Static MP4 files in `frontend/public/showcase/` — baked into the container image, no GCS needed.

To regenerate:

```bash
cd scripts
pip install google-genai google-cloud-storage
python generate_showcase.py
# Saves to frontend/public/showcase/
```
