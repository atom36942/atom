#!/usr/bin/env bash
set -euo pipefail

# Bootstrap deploy for the Atom staging environment on Azure.
#
# Idempotent: running it again will redeploy Bicep (no-op on unchanged resources)
# and rebuild the container image with new tag :latest.
#
# Required: az CLI logged in to "Elevate Azure subscription GroupFF".
# Run from the repo root: ./infra/deploy.sh

SUB_NAME="${SUB_NAME:-Elevate Azure subscription GroupFF}"
LOC="${LOC:-southeastasia}"
RG="${RG:-rg-mgh-atom}"
APP_NAME="${APP_NAME:-app-mgh-atom-stg}"
ACR_NAME="${ACR_NAME:-crmghatomstg}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Setting subscription: $SUB_NAME"
az account set --subscription "$SUB_NAME"

echo "==> Ensuring resource group: $RG ($LOC)"
az group create -n "$RG" -l "$LOC" -o none

# Generate secrets only on first deploy (skip if KV already has them)
KV_NAME="kv-mghatomstg"
PG_PASSWORD=""
TOKEN_SECRET=""
if az keyvault secret show --vault-name "$KV_NAME" --name postgresAdminPassword -o none 2>/dev/null; then
  echo "==> Reusing existing secrets from Key Vault $KV_NAME"
  PG_PASSWORD=$(az keyvault secret show --vault-name "$KV_NAME" --name postgresAdminPassword --query value -o tsv)
  TOKEN_SECRET=$(az keyvault secret show --vault-name "$KV_NAME" --name tokenSecret --query value -o tsv)
else
  echo "==> Generating fresh Postgres admin password and token secret"
  PG_PASSWORD=$(openssl rand -base64 32 | tr -d '/+=' | cut -c1-28)
  TOKEN_SECRET=$(openssl rand -hex 32)
fi

echo "==> Deploying Bicep (this provisions everything; ~10-15 min for first run)"
DEPLOY_NAME="atom-stg-$(date +%Y%m%d-%H%M%S)"
export POSTGRES_ADMIN_PASSWORD="$PG_PASSWORD"
export TOKEN_SECRET="$TOKEN_SECRET"
az deployment group create \
  -g "$RG" \
  -f infra/main.bicep \
  -p infra/parameters.staging.bicepparam \
  -n "$DEPLOY_NAME" \
  -o table

ACR_LOGIN_SERVER=$(az deployment group show -g "$RG" -n "$DEPLOY_NAME" --query properties.outputs.acrLoginServer.value -o tsv)
APP=$(az deployment group show -g "$RG" -n "$DEPLOY_NAME" --query properties.outputs.appName.value -o tsv)

echo "==> Building image with az acr build (replaces placeholder): $ACR_NAME/atom:latest"
az acr build --registry "$ACR_NAME" --image atom:latest --image "atom:initial-$(git rev-parse --short HEAD 2>/dev/null || date +%s)" .

echo "==> Pointing App Service at the real image"
az webapp config container set \
  -g "$RG" -n "$APP" \
  --container-image-name "$ACR_LOGIN_SERVER/atom:latest" -o none

echo "==> Restarting App Service"
az webapp restart -g "$RG" -n "$APP" -o none

echo
echo "==> Done."
echo "    App URL : https://$APP.azurewebsites.net"
echo "    Health  : https://$APP.azurewebsites.net/health"
echo "    Logs    : az webapp log tail -g $RG -n $APP"
echo
echo "    First container pull takes 3-5 min after restart; tail logs to watch."
