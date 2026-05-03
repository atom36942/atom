param location string
param name string
param tenantId string = subscription().tenantId
param uamiPrincipalId string

param pgFqdn string
param pgAdminLogin string
param pgDatabaseName string

@secure()
param postgresAdminPassword string

param redisHostName string
param redisPort int

@secure()
param redisPrimaryKey string

@secure()
param tokenSecret string

resource kv 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: name
  location: location
  properties: {
    tenantId: tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enabledForTemplateDeployment: true
    publicNetworkAccess: 'Enabled'
    softDeleteRetentionInDays: 7
  }
}

resource pgPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2024-04-01-preview' = {
  parent: kv
  name: 'postgresAdminPassword'
  properties: {
    value: postgresAdminPassword
  }
}

resource pgConnSecret 'Microsoft.KeyVault/vaults/secrets@2024-04-01-preview' = {
  parent: kv
  name: 'postgresConnectionString'
  properties: {
    value: 'postgresql://${pgAdminLogin}:${postgresAdminPassword}@${pgFqdn}:5432/${pgDatabaseName}?sslmode=require'
  }
}

resource redisKeySecret 'Microsoft.KeyVault/vaults/secrets@2024-04-01-preview' = {
  parent: kv
  name: 'redisPrimaryKey'
  properties: {
    value: redisPrimaryKey
  }
}

resource redisConnSecret 'Microsoft.KeyVault/vaults/secrets@2024-04-01-preview' = {
  parent: kv
  name: 'redisConnectionString'
  properties: {
    value: 'rediss://:${redisPrimaryKey}@${redisHostName}:${redisPort}/0'
  }
}

resource tokenSecretRes 'Microsoft.KeyVault/vaults/secrets@2024-04-01-preview' = {
  parent: kv
  name: 'tokenSecret'
  properties: {
    value: tokenSecret
  }
}

var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource uamiKvAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: kv
  name: guid(kv.id, uamiPrincipalId, kvSecretsUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', kvSecretsUserRoleId)
    principalId: uamiPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output id string = kv.id
output name string = kv.name
output uri string = kv.properties.vaultUri
output postgresConnectionStringSecretUri string = '${kv.properties.vaultUri}secrets/postgresConnectionString'
output redisConnectionStringSecretUri string = '${kv.properties.vaultUri}secrets/redisConnectionString'
output tokenSecretUri string = '${kv.properties.vaultUri}secrets/tokenSecret'
