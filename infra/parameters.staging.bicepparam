using 'main.bicep'

param location = 'southeastasia'

// First deploy uses the public placeholder image. After deploy.sh builds and pushes
// crmghatomstg.azurecr.io/atom:latest, the App Service is repointed via
// `az webapp config container set` -- no need to redeploy Bicep just for the image.
param containerImage = 'mcr.microsoft.com/appsvc/staticsite:latest'

// Set to e.g. '1' if name collisions occur on globally-unique resources
// (acr / storage / kv) and re-deploy.
param uniqueSuffix = ''

// Secrets are sourced from environment variables that deploy.sh exports.
// Never put real secrets in this file.
param postgresAdminPassword = readEnvironmentVariable('POSTGRES_ADMIN_PASSWORD', '')
param tokenSecret = readEnvironmentVariable('TOKEN_SECRET', '')
