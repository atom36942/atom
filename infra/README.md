# infra/ — Atom staging on Azure

Bicep-based deployment for the Atom FastAPI app to **Azure Southeast Asia (Singapore)** in resource group `rg-mgh-atom`, subscription `Elevate Azure subscription GroupFF`.

## Stack

| Resource | SKU | Cost (retail) |
|---|---|---:|
| App Service Plan (Linux) | B1 | $13.14 /mo |
| App Service (container) | n/a | (incl.) |
| Postgres Flex Server | B1MS, 32 GB | $23.40 /mo |
| Azure Managed Redis | Balanced_B0 | $14.60 /mo |
| Container Registry | Basic | $5 /mo |
| Storage Account | Standard_LRS | <$2 /mo |
| Log Analytics + App Insights | PerGB2018 | $0 (under 5 GB free) |
| Key Vault | Standard | ~$0 |
| **Total** | | **≈ $58/mo** |

## Files

- `main.bicep` — RG-scoped orchestrator
- `parameters.staging.bicepparam` — typed param file
- `modules/identity.bicep` — User-Assigned Managed Identity (ACR pull + GH OIDC)
- `modules/observability.bicep` — Log Analytics workspace + App Insights
- `modules/acr.bicep` — Container Registry Basic + AcrPull role
- `modules/storage.bicep` — Storage account + blob container `general`
- `modules/postgres.bicep` — Flex Server + database + firewall + extensions
- `modules/redis.bicep` — Azure Managed Redis (Balanced_B0)
- `modules/keyvault.bicep` — Key Vault + secrets (passwords + connection strings)
- `modules/app.bicep` — App Service Plan + App Service + diagnostic settings
- `deploy.sh` — bootstrap: RG → Bicep → first image build → swap to real image

## First-time deploy

Prereqs:
- `az` CLI logged in: `az login`
- Subscription set: `az account set --subscription "Elevate Azure subscription GroupFF"`
- Repo root as working directory

```bash
./infra/deploy.sh
```

Steps the script runs:
1. `az group create rg-mgh-atom`
2. Generates Postgres admin password + JWT token secret with `openssl`
3. `az deployment group create` — provisions all resources (placeholder container image)
4. `az acr build` — builds and pushes `atom:latest` from the repo Dockerfile
5. `az webapp config container set` — swaps placeholder → real image
6. `az webapp restart`

Expected duration: **10–15 minutes** for first deploy (Postgres + Managed Redis are slow to provision).

After first deploy, set up GitHub OIDC for CI:

```bash
RG=rg-mgh-atom
SUB_ID=$(az account show --query id -o tsv)
PRINCIPAL=$(az identity show -g $RG -n uami-mgh-atom-stg --query principalId -o tsv)

# Federated credential for branch main
az identity federated-credential create \
  -g $RG --identity-name uami-mgh-atom-stg \
  --name gh-main \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:MGH-IT/mgh-atom:ref:refs/heads/main \
  --audiences api://AzureADTokenExchange

# Federated credential for workflow_dispatch via 'staging' environment
az identity federated-credential create \
  -g $RG --identity-name uami-mgh-atom-stg \
  --name gh-dispatch \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:MGH-IT/mgh-atom:environment:staging \
  --audiences api://AzureADTokenExchange

# Grant UAMI Contributor on the RG
az role assignment create --assignee "$PRINCIPAL" --role Contributor \
  --scope "/subscriptions/$SUB_ID/resourceGroups/$RG"
```

Then set repo secrets in `MGH-IT/mgh-atom`:

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | `az identity show -g rg-mgh-atom -n uami-mgh-atom-stg --query clientId -o tsv` |
| `AZURE_TENANT_ID` | `788d1c79-6f4b-4f0c-9d23-6792c2ad6ce3` |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id -o tsv` |
| `AZURE_RG` | `rg-mgh-atom` |
| `AZURE_ACR` | `crmghatomstg` |
| `AZURE_APP` | `app-mgh-atom-stg` |

Push to `main` to trigger the deploy workflow.

## Verifying

```bash
APP=https://app-mgh-atom-stg.azurewebsites.net
curl -fsS $APP/health
curl -fsS $APP/info | jq '.message | {schema_keys: (.postgres_schema | keys), api_count: (.api_list | length)}'
az webapp log tail -g rg-mgh-atom -n app-mgh-atom-stg
```

Direct Postgres access (firewall open to all IPs, staging only):

```bash
PG_PASSWORD=$(az keyvault secret show --vault-name kv-mghatomstg --name postgresAdminPassword --query value -o tsv)
psql "postgresql://atomadmin:$PG_PASSWORD@pg-mgh-atom-stg.postgres.database.azure.com:5432/atom?sslmode=require" -c "\dt"
```

## Operating notes

- **Re-running `deploy.sh`** is safe — Bicep is idempotent; `az acr build` rebuilds with the same `:latest` tag.
- **Routine updates** flow through GitHub Actions, not `deploy.sh`. Pushing to `main` triggers a build + container swap.
- **Bicep redeploys** reset `linuxFxVersion` to the placeholder unless you pass `-p containerImage=$(current image)`. Easiest: don't redeploy Bicep unless adding/changing infra; let GH Actions own image rotation.
- **Rotating the Postgres password**: update the KV secret `postgresAdminPassword`, run `az postgres flexible-server update --admin-password ...`, restart the app.
- **Rotating the token secret**: update KV secret `tokenSecret`, restart the app. Existing JWTs become invalid.

## Footguns to avoid

- Don't carry the wide-open Postgres firewall (`AllowAllPublic` = `0.0.0.0`–`255.255.255.255`) into production. Replace with explicit allow-list, VNet, or private endpoint.
- Don't reduce App Service to F1 / D1 (no Always On, no custom domain SSL on Linux).
- Don't use legacy `Microsoft.Cache/Redis` — this stack uses the new `Microsoft.Cache/redisEnterprise` (Azure Managed Redis) on TLS port 10000.
- Don't enable the ACR admin user — managed identity does the pull.
- Don't omit `WEBSITES_PORT=8000`; without it App Service routes to port 80 in the container.

## Tearing down

```bash
az group delete -n rg-mgh-atom --yes
```

Soft-deleted Key Vault is purged after 7 days (set in module). To re-deploy with the same KV name within 7 days, append a `uniqueSuffix` parameter or run `az keyvault purge -n kv-mghatomstg`.
