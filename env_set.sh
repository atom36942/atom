# Run using: bash env_set.sh

#!/usr/bin/env bash

set -euo pipefail

RESOURCE_GROUP="rg-mgh-atom"
APP_NAME="app-mgh-atom-stg"
RESTART_APP="false" # Set to "true" to force an explicit restart (App Settings updates already auto-restart the app)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: .env file not found at $ENV_FILE"
  exit 1
fi

ENV_VARS=()

while IFS= read -r LINE || [[ -n "$LINE" ]]; do
  LINE="${LINE%$'\r'}"

  [[ -z "$LINE" ]] && continue
  [[ "$LINE" =~ ^[[:space:]]*# ]] && continue

  KEY="${LINE%%=*}"

  if [[ "$KEY" != config_* ]]; then
    continue
  fi

  ENV_VARS+=("$LINE")
done < "$ENV_FILE"

if (( ${#ENV_VARS[@]} == 0 )); then
  echo "Error: No config_* variables found in .env"
  exit 1
fi

echo "Setting ${#ENV_VARS[@]} config_* variables..."

az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --settings "${ENV_VARS[@]}" \
  --output none

KEEP_KEYS=()

for ENV_VAR in "${ENV_VARS[@]}"; do
  KEEP_KEYS+=("${ENV_VAR%%=*}")
done

EXISTING_KEYS="$(
  az webapp config appsettings list \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --query "[?starts_with(name, 'config_')].name" \
    --output tsv
)"

EXTRA_KEYS=()

while IFS= read -r EXISTING_KEY; do
  [[ -z "$EXISTING_KEY" ]] && continue

  KEEP=false

  for KEEP_KEY in "${KEEP_KEYS[@]}"; do
    if [[ "$EXISTING_KEY" == "$KEEP_KEY" ]]; then
      KEEP=true
      break
    fi
  done

  if [[ "$KEEP" == false ]]; then
    EXTRA_KEYS+=("$EXISTING_KEY")
  fi
done <<< "$EXISTING_KEYS"

if (( ${#EXTRA_KEYS[@]} > 0 )); then
  echo "Deleting extra config_* variables:"
  printf '  %s\n' "${EXTRA_KEYS[@]}"

  az webapp config appsettings delete \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME" \
    --setting-names "${EXTRA_KEYS[@]}" \
    --output none
fi

if [[ "$RESTART_APP" == "true" ]]; then
  echo "Restarting web app..."
  az webapp restart \
    --resource-group "$RESOURCE_GROUP" \
    --name "$APP_NAME"
fi

echo "Final config_* keys:"

az webapp config appsettings list \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --query "[?starts_with(name, 'config_')].name" \
  --output table