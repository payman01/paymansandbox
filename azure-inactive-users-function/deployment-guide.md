# Deployment Guide for Azure Inactive Users Scanner

This guide provides step-by-step instructions for deploying the Azure Function that scans for inactive users.

## Prerequisites Checklist

- [ ] Azure subscription with appropriate permissions
- [ ] Azure CLI installed and configured
- [ ] Azure Functions Core Tools installed
- [ ] Python 3.9+ installed locally (for testing)

## Step 1: Create Azure Resources

### 1.1 Create Resource Group

```bash
az group create \
  --name rg-inactive-users-scanner \
  --location eastus
```

### 1.2 Create Storage Account

```bash
az storage account create \
  --name stinactiveusers$(date +%s) \
  --resource-group rg-inactive-users-scanner \
  --location eastus \
  --sku Standard_LRS
```

### 1.3 Create Function App

```bash
az functionapp create \
  --resource-group rg-inactive-users-scanner \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --name func-inactive-users-$(date +%s) \
  --storage-account stinactiveusers$(date +%s)
```

## Step 2: Azure AD App Registration

### 2.1 Create App Registration

```bash
# Create the app registration
az ad app create \
  --display-name "Inactive Users Scanner" \
  --sign-in-audience AzureADMyOrg

# Note the appId from the output - this is your CLIENT_ID
```

### 2.2 Create Service Principal

```bash
# Replace <APP_ID> with the appId from previous step
az ad sp create --id <APP_ID>
```

### 2.3 Create Client Secret

```bash
# Replace <APP_ID> with your app ID
az ad app credential reset \
  --id <APP_ID> \
  --display-name "Function App Secret"

# Note the password from the output - this is your CLIENT_SECRET
```

### 2.4 Grant API Permissions

```bash
# Get Microsoft Graph App ID
GRAPH_APP_ID="00000003-0000-0000-c000-000000000000"

# Grant User.Read.All permission
az ad app permission add \
  --id <APP_ID> \
  --api $GRAPH_APP_ID \
  --api-permissions df021288-bdef-4463-88db-98f22de89214=Role

# Grant AuditLog.Read.All permission  
az ad app permission add \
  --id <APP_ID> \
  --api $GRAPH_APP_ID \
  --api-permissions b0afded3-3588-46d8-8b3d-9842eff778da=Role

# Grant admin consent
az ad app permission admin-consent --id <APP_ID>
```

## Step 3: Configure Environment Variables

### 3.1 Get Required Values

```bash
# Get Tenant ID
az account show --query tenantId -o tsv

# Get Storage Connection String
az storage account show-connection-string \
  --name <STORAGE_ACCOUNT_NAME> \
  --resource-group rg-inactive-users-scanner \
  --query connectionString -o tsv
```

### 3.2 Set Function App Settings

```bash
# Replace placeholders with actual values
az functionapp config appsettings set \
  --name <FUNCTION_APP_NAME> \
  --resource-group rg-inactive-users-scanner \
  --settings \
    TENANT_ID="<YOUR_TENANT_ID>" \
    CLIENT_ID="<YOUR_CLIENT_ID>" \
    CLIENT_SECRET="<YOUR_CLIENT_SECRET>" \
    STORAGE_CONNECTION_STRING="<YOUR_STORAGE_CONNECTION_STRING>" \
    BLOB_CONTAINER_NAME="inactive-users-reports"
```

## Step 4: Deploy Function Code

### 4.1 Prepare Deployment Package

```bash
# Navigate to function directory
cd azure-inactive-users-function

# Create deployment package
zip -r ../function-app.zip . -x "*.git*" "*.vscode*" "__pycache__*" "*.pyc"
```

### 4.2 Deploy to Azure

```bash
# Deploy using Azure CLI
az functionapp deployment source config-zip \
  --resource-group rg-inactive-users-scanner \
  --name <FUNCTION_APP_NAME> \
  --src function-app.zip
```

### 4.3 Alternative: Deploy using Azure Functions Core Tools

```bash
# Login to Azure
az login

# Deploy function
func azure functionapp publish <FUNCTION_APP_NAME>
```

## Step 5: Create Blob Storage Container

```bash
# Create container for reports
az storage container create \
  --name inactive-users-reports \
  --account-name <STORAGE_ACCOUNT_NAME> \
  --auth-mode login
```

## Step 6: Verification and Testing

### 6.1 Verify Function Deployment

```bash
# List functions in the app
az functionapp function list \
  --name <FUNCTION_APP_NAME> \
  --resource-group rg-inactive-users-scanner
```

### 6.2 Test Function Execution

1. Go to Azure Portal
2. Navigate to your Function App
3. Select "Functions" > "InactiveUsersScanner"
4. Click "Test/Run"
5. Click "Run" to execute

### 6.3 Check Logs

```bash
# Stream logs
az webapp log tail \
  --name <FUNCTION_APP_NAME> \
  --resource-group rg-inactive-users-scanner
```

## Step 7: Configure Monitoring (Optional)

### 7.1 Enable Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app inactive-users-insights \
  --location eastus \
  --resource-group rg-inactive-users-scanner

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app inactive-users-insights \
  --resource-group rg-inactive-users-scanner \
  --query instrumentationKey -o tsv)

# Configure Function App to use Application Insights
az functionapp config appsettings set \
  --name <FUNCTION_APP_NAME> \
  --resource-group rg-inactive-users-scanner \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="$INSTRUMENTATION_KEY"
```

## Step 8: Security Hardening

### 8.1 Use Managed Identity (Recommended)

```bash
# Enable system-assigned managed identity
az functionapp identity assign \
  --name <FUNCTION_APP_NAME> \
  --resource-group rg-inactive-users-scanner

# Get the principal ID
PRINCIPAL_ID=$(az functionapp identity show \
  --name <FUNCTION_APP_NAME> \
  --resource-group rg-inactive-users-scanner \
  --query principalId -o tsv)

# Grant permissions to the managed identity
az ad app permission grant \
  --id $PRINCIPAL_ID \
  --api 00000003-0000-0000-c000-000000000000
```

### 8.2 Use Key Vault for Secrets (Recommended)

```bash
# Create Key Vault
az keyvault create \
  --name kv-inactive-users-$(date +%s) \
  --resource-group rg-inactive-users-scanner \
  --location eastus

# Store secrets
az keyvault secret set \
  --vault-name <KEY_VAULT_NAME> \
  --name "CLIENT-SECRET" \
  --value "<YOUR_CLIENT_SECRET>"

# Update function app settings to use Key Vault references
az functionapp config appsettings set \
  --name <FUNCTION_APP_NAME> \
  --resource-group rg-inactive-users-scanner \
  --settings CLIENT_SECRET="@Microsoft.KeyVault(VaultName=<KEY_VAULT_NAME>;SecretName=CLIENT-SECRET)"
```

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   - Verify admin consent was granted
   - Check API permissions are correctly configured

2. **Function Not Triggering**
   - Verify timer trigger configuration
   - Check function app is running

3. **Storage Access Issues**
   - Verify storage connection string
   - Check container exists and permissions

4. **Graph API Errors**
   - Verify tenant ID, client ID, and secret
   - Check token acquisition in logs

### Useful Commands

```bash
# Check function status
az functionapp show \
  --name <FUNCTION_APP_NAME> \
  --resource-group rg-inactive-users-scanner \
  --query state

# Restart function app
az functionapp restart \
  --name <FUNCTION_APP_NAME> \
  --resource-group rg-inactive-users-scanner

# View recent logs
az webapp log download \
  --name <FUNCTION_APP_NAME> \
  --resource-group rg-inactive-users-scanner
```

## Cleanup

To remove all resources:

```bash
az group delete \
  --name rg-inactive-users-scanner \
  --yes --no-wait
```

## Next Steps

1. Set up monitoring and alerting
2. Configure backup and disaster recovery
3. Implement additional security measures
4. Set up automated testing
5. Create documentation for your team

