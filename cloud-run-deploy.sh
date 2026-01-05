#!/bin/bash
# Google Cloud Run Deployment Script for TWBA Dashboard
#
# This script reads configuration from .env file. Create a .env file with:
#   GCP_PROJECT_ID=your-project-id
#   GCP_REGION=us-central1
#   SERVICE_NAME=twba-dashboard (optional, defaults to twba-dashboard)
#   MEMORY=2Gi (optional, defaults to 2Gi)
#   CPU=2 (optional, defaults to 2)
#   TIMEOUT=300 (optional, defaults to 300)
#   MAX_INSTANCES=10 (optional, defaults to 10)
#   SUPABASE_KEY_SECRET=supabase-key (optional, defaults to supabase-key)
#   OPENAI_API_KEY_SECRET=openai-key (optional, defaults to openai-key)
#   DB_CONNECTION_STRING_SECRET=db-connection-string (optional, defaults to db-connection-string)
#   PASSWORD_SECRET=auth-password (optional, defaults to auth-password)
#
# You can also set these as environment variables instead of using .env file.

set -e  # Exit on error

# Function to load .env file
load_env_file() {
    if [ -f .env ]; then
        echo "Loading environment variables from .env file..."
        # Read .env file line by line, ignoring comments and empty lines
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip comments and empty lines
            if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
                continue
            fi
            # Export the variable (handles KEY=VALUE format)
            if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
                key="${BASH_REMATCH[1]// /}"
                value="${BASH_REMATCH[2]}"
                # Remove quotes if present
                value="${value#\"}"
                value="${value%\"}"
                value="${value#\'}"
                value="${value%\'}"
                export "$key=$value"
            fi
        done < .env
    else
        echo "Warning: .env file not found. Using environment variables or defaults."
    fi
}

# Load .env file
load_env_file

# Configuration - read from .env, then environment variables, then defaults
PROJECT_ID="${GCP_PROJECT_ID:-portfolioapp-348a9}"
REGION="${GCP_REGION:-asia-southeast1}"
SERVICE_NAME="${SERVICE_NAME:-twba-dashboard}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== TWBA Dashboard Cloud Run Deployment ===${NC}\n"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed.${NC}"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}Not authenticated. Running gcloud auth login...${NC}"
    gcloud auth login
fi

# Validate PROJECT_ID
if [ "${PROJECT_ID}" = "your-project-id" ] || [ -z "${PROJECT_ID}" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID is not set or is using default value.${NC}"
    echo "Please set GCP_PROJECT_ID in your .env file or as an environment variable."
    echo "Example: GCP_PROJECT_ID=your-actual-project-id"
    exit 1
fi

# Set the project
echo -e "${GREEN}Setting GCP project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${GREEN}Enabling required APIs...${NC}"
echo "This may take a few moments..."
gcloud services enable cloudbuild.googleapis.com --quiet
gcloud services enable run.googleapis.com --quiet
gcloud services enable containerregistry.googleapis.com --quiet
gcloud services enable artifactregistry.googleapis.com --quiet

echo -e "${GREEN}APIs enabled successfully!${NC}"

# Build and push the container image
echo -e "${GREEN}Building and pushing container image...${NC}"
gcloud builds submit --tag ${IMAGE_NAME}

# Deploy to Cloud Run
echo -e "${GREEN}Deploying to Cloud Run...${NC}"

# Check if service exists
SERVICE_EXISTS=false
if gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format="value(status.url)" &>/dev/null; then
    SERVICE_EXISTS=true
    echo -e "${YELLOW}Service exists. Existing environment variables will be preserved.${NC}"
fi

# Build deploy command array
DEPLOY_ARGS=(
    "gcloud" "run" "deploy" "${SERVICE_NAME}"
    "--image" "${IMAGE_NAME}"
    "--platform" "managed"
    "--region" "${REGION}"
    "--allow-unauthenticated"
    "--port" "8050"
    "--memory" "${MEMORY:-2Gi}"
    "--cpu" "${CPU:-2}"
    "--timeout" "${TIMEOUT:-300}"
    "--max-instances" "${MAX_INSTANCES:-10}"
)

# Only set environment variables if service doesn't exist (new deployment)
# If service exists, existing env vars will be preserved automatically by Cloud Run
if [ "$SERVICE_EXISTS" = false ] && [ -f .env ]; then
    # New service - set env vars from .env file
    ENV_VARS=""
    
    # Read values from .env file
    SUPABASE_VAL=$(grep -E "^SUPABASE_KEY=" .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "")
    OPENAI_VAL=$(grep -E "^OPENAI_API_KEY=" .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "")
    DB_VAL=$(grep -E "^DB_CONNECTION_STRING=" .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "")
    PASSWORD_VAL=$(grep -E "^PASSWORD=" .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" || echo "")
    
    # Build env vars string
    [ -n "${SUPABASE_VAL}" ] && ENV_VARS="${ENV_VARS}SUPABASE_KEY=${SUPABASE_VAL},"
    [ -n "${OPENAI_VAL}" ] && ENV_VARS="${ENV_VARS}OPENAI_API_KEY=${OPENAI_VAL},"
    [ -n "${DB_VAL}" ] && ENV_VARS="${ENV_VARS}DB_CONNECTION_STRING=${DB_VAL},"
    [ -n "${PASSWORD_VAL}" ] && ENV_VARS="${ENV_VARS}PASSWORD=${PASSWORD_VAL},"
    
    # Remove trailing comma and add env vars if we have any
    if [ -n "${ENV_VARS}" ]; then
        ENV_VARS="${ENV_VARS%,}"  # Remove trailing comma
        DEPLOY_ARGS+=("--set-env-vars" "${ENV_VARS}")
        echo -e "${GREEN}Setting environment variables from .env file${NC}"
    fi
else
    if [ "$SERVICE_EXISTS" = true ]; then
        echo -e "${YELLOW}Preserving existing environment variables${NC}"
    fi
fi

# Execute the deploy command
"${DEPLOY_ARGS[@]}"

echo -e "\n${GREEN}=== Deployment Complete! ===${NC}"
echo -e "${GREEN}Your service URL:${NC}"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format="value(status.url)"

echo -e "\n${YELLOW}Note: Make sure to create secrets in Secret Manager:${NC}"
echo "  - supabase-key"
echo "  - openai-key (optional)"
echo "  - db-connection-string (optional)"
echo "  - auth-password"

