param location string
param name string

resource redisCluster 'Microsoft.Cache/redisEnterprise@2024-10-01' = {
  name: name
  location: location
  sku: {
    name: 'Balanced_B0'
  }
}

resource redisDb 'Microsoft.Cache/redisEnterprise/databases@2024-10-01' = {
  parent: redisCluster
  name: 'default'
  properties: {
    clusteringPolicy: 'EnterpriseCluster'
    evictionPolicy: 'NoEviction'
    port: 10000
    clientProtocol: 'Encrypted'
  }
}

output clusterName string = redisCluster.name
output hostName string = redisCluster.properties.hostName
output port int = redisDb.properties.port

@secure()
output primaryKey string = redisDb.listKeys().primaryKey
