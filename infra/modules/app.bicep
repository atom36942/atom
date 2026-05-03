param location string
param aspName string
param appName string

param uamiId string
param uamiClientId string

param containerImage string = 'mcr.microsoft.com/appsvc/staticsite:latest'

param appInsightsConnectionString string
param appInsightsInstrumentationKey string
param logAnalyticsId string

param keyVaultUri string
param postgresConnectionStringSecretName string = 'postgresConnectionString'
param redisConnectionStringSecretName string = 'redisConnectionString'
param tokenSecretName string = 'tokenSecret'

param dockerRegistryUrl string

resource asp 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: aspName
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

var pgUrlRef = '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/${postgresConnectionStringSecretName}/)'
var redisUrlRef = '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/${redisConnectionStringSecretName}/)'
var tokenSecretRef = '@Microsoft.KeyVault(SecretUri=${keyVaultUri}secrets/${tokenSecretName}/)'

resource site 'Microsoft.Web/sites@2023-12-01' = {
  name: appName
  location: location
  kind: 'app,linux,container'
  identity: {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${uamiId}': {}
    }
  }
  properties: {
    serverFarmId: asp.id
    httpsOnly: true
    keyVaultReferenceIdentity: uamiId
    siteConfig: {
      linuxFxVersion: 'DOCKER|${containerImage}'
      acrUseManagedIdentityCreds: true
      acrUserManagedIdentityID: uamiClientId
      healthCheckPath: '/health'
      alwaysOn: true
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      use32BitWorkerProcess: false
      http20Enabled: true
      appSettings: [
        { name: 'WEBSITES_PORT', value: '8000' }
        { name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE', value: 'false' }
        { name: 'WEBSITES_CONTAINER_START_TIME_LIMIT', value: '600' }
        { name: 'DOCKER_REGISTRY_SERVER_URL', value: dockerRegistryUrl }
        { name: 'PORT', value: '8000' }
        { name: 'PYTHONUNBUFFERED', value: '1' }
        { name: 'config_postgres_url', value: pgUrlRef }
        { name: 'config_redis_url', value: redisUrlRef }
        { name: 'config_redis_url_ratelimiter', value: redisUrlRef }
        { name: 'config_redis_url_pubsub', value: redisUrlRef }
        { name: 'config_celery_broker_url', value: redisUrlRef }
        { name: 'config_celery_backend_url', value: redisUrlRef }
        { name: 'config_token_secret_key', value: tokenSecretRef }
        { name: 'config_is_postgres_init_startup', value: '1' }
        { name: 'config_is_signup', value: '1' }
        { name: 'config_is_log_api', value: '1' }
        { name: 'config_is_traceback', value: '1' }
        { name: 'config_is_reset_tmp', value: '0' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
        { name: 'APPINSIGHTS_INSTRUMENTATIONKEY', value: appInsightsInstrumentationKey }
        { name: 'ApplicationInsightsAgent_EXTENSION_VERSION', value: '~3' }
      ]
    }
  }
}

resource diagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: site
  name: 'send-to-law'
  properties: {
    workspaceId: logAnalyticsId
    logs: [
      { category: 'AppServiceConsoleLogs', enabled: true }
      { category: 'AppServiceHTTPLogs', enabled: true }
      { category: 'AppServiceAppLogs', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

output name string = site.name
output defaultHostName string = site.properties.defaultHostName
output systemAssignedPrincipalId string = site.identity.principalId
output id string = site.id
