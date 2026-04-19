#!/usr/bin/env bash
# setup.sh — Automated setup for Gemini Motion Lab
#
# Creates:
#   1. GCS bucket for video storage
#   2. Service account for backend access
#   3. .env file with all required environment variables
#
# Usage:
#   chmod +x setup.sh && ./setup.sh

set -euo pipefail

# ── Resolve project ID ──────────────────────────────────────────────────────
PROJECT_FILE="$HOME/project_id.txt"
if [ -s "$PROJECT_FILE" ]; then
    PROJECT_ID=$(cat "$PROJECT_FILE" | tr -d '[:space:]')
    echo "Using project ID from $PROJECT_FILE: $PROJECT_ID"
else
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
    echo "❌ No project set. Run ./init.sh first, or: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

REGION="us-central1"
BUCKET_NAME="gemini-motion-lab-${PROJECT_ID}"
SA_NAME="gemini-motion-lab-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=============================================="
echo "  Gemini Motion Lab — Setup"
echo "=============================================="
echo ""
echo "  Project:          $PROJECT_ID"
echo "  Region:           $REGION"
echo "  Bucket:           $BUCKET_NAME"
echo "  Service Account:  $SA_EMAIL"
echo ""

# ── Step 1: Create GCS Bucket ───────────────────────────────────────────────
echo "🪣 Creating GCS bucket..."
if gsutil ls -b "gs://${BUCKET_NAME}" &>/dev/null; then
    echo "   ✅ Bucket gs://${BUCKET_NAME} already exists"
else
    gsutil mb -l "$REGION" "gs://${BUCKET_NAME}"
    echo "   ✅ Created gs://${BUCKET_NAME}"
fi

# Set CORS for browser uploads
echo '[{"origin": ["*"], "method": ["GET","PUT","POST"], "responseHeader": ["Content-Type"], "maxAgeSeconds": 3600}]' > /tmp/cors.json
gsutil cors set /tmp/cors.json "gs://${BUCKET_NAME}"
rm /tmp/cors.json
echo "   ✅ CORS configured"

# ── Step 2: Create Service Account ──────────────────────────────────────────
echo ""
echo "🔑 Creating service account..."
if gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
    echo "   ✅ Service account $SA_EMAIL already exists"
else
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Gemini Motion Lab SA" \
        --project="$PROJECT_ID"
    echo "   ✅ Created $SA_EMAIL"
fi

# ── Step 3: Generate .env file ──────────────────────────────────────────────
echo ""
echo "📝 Generating .env file..."

ENV_FILE="$(cd "$(dirname "$0")" && pwd)/.env"

cat > "$ENV_FILE" <<EOF
GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
GOOGLE_CLOUD_LOCATION=${REGION}
GCS_BUCKET=${BUCKET_NAME}
GCS_SIGNING_SA=${SA_EMAIL}
GOOGLE_GENAI_USE_VERTEXAI=true
MOCK_AI=false
PUBLIC_BASE_URL=http://localhost:8000
EOF

echo "   ✅ Created $ENV_FILE"

# ── Done ────────────────────────────────────────────────────────────────────
echo ""
echo "=============================================="
echo "  ✅ Setup complete!"
echo "=============================================="
echo ""
echo "  Next steps:"
echo "  1. Grant IAM roles (see codelab for commands)"
echo "  2. Deploy the backend:  gcloud run deploy ..."
echo "  3. Deploy the frontend: gcloud run deploy ..."
echo ""
