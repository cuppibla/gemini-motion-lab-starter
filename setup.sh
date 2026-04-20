#!/usr/bin/env bash
# setup.sh — Automated setup for Gemini Motion Lab
#
# Creates:
#   1. Service account for backend access
#   2. GCS bucket for video storage (with CORS)
#   3. IAM role bindings for the service account
#   4. .env file with all required environment variables
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

# ── Step 1: Create Service Account ──────────────────────────────────────────
echo "🔑 Creating service account..."
if gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
    echo "   ✅ Service account $SA_EMAIL already exists"
else
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Gemini Motion Lab SA" \
        --project="$PROJECT_ID"
    echo "   ✅ Created $SA_EMAIL"
fi

# ── Step 2: Grant IAM roles ─────────────────────────────────────────────────
echo ""
echo "🛡️  Granting IAM roles..."

# Grant Storage Admin to service account
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.admin" \
    --quiet > /dev/null 2>&1
echo "   ✅ Granted roles/storage.admin to service account"

# Grant Vertex AI User to service account
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/aiplatform.user" \
    --quiet > /dev/null 2>&1
echo "   ✅ Granted roles/aiplatform.user to service account"

# Grant Service Account Token Creator to the Compute Engine default SA
COMPUTE_SA=$(gcloud iam service-accounts list \
    --format="value(email)" \
    --filter="displayName:Compute Engine default service account" \
    --project="$PROJECT_ID" 2>/dev/null || true)

if [ -n "$COMPUTE_SA" ]; then
    gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
        --member="serviceAccount:${COMPUTE_SA}" \
        --role="roles/iam.serviceAccountTokenCreator" \
        --quiet > /dev/null 2>&1
    echo "   ✅ Granted roles/iam.serviceAccountTokenCreator to Compute SA"
else
    echo "   ⚠️  Compute Engine default SA not found — you'll need to grant Token Creator manually after first deploy"
fi

# ── Step 3: Create GCS Bucket ───────────────────────────────────────────────
echo ""
echo "🪣 Creating GCS bucket..."
if gcloud storage buckets describe "gs://${BUCKET_NAME}" &>/dev/null; then
    echo "   ✅ Bucket gs://${BUCKET_NAME} already exists"
else
    gcloud storage buckets create "gs://${BUCKET_NAME}" --location="$REGION" --project="$PROJECT_ID"
    echo "   ✅ Created gs://${BUCKET_NAME}"
fi

# Set CORS for browser uploads
echo '[{"origin": ["*"], "method": ["GET","PUT","POST"], "responseHeader": ["Content-Type"], "maxAgeSeconds": 3600}]' > /tmp/cors.json
gcloud storage buckets update "gs://${BUCKET_NAME}" --cors-file=/tmp/cors.json
rm /tmp/cors.json
echo "   ✅ CORS configured"

# ── Step 4: Generate .env file ──────────────────────────────────────────────
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
echo "  1. Deploy the backend:  see codelab for commands"
echo "  2. Deploy the frontend: see codelab for commands"
echo ""
