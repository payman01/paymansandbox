# Azure Inactive Users Report Function - Deployment Guide

This Azure Function generates a weekly report of users who haven't logged into your Azure AD tenant in the past 30 days. The report is saved as a CSV file in Azure Blob Storage.

## 📋 Prerequisites

- Azure subscription with appropriate permissions
- Azure AD tenant with Global Administrator or User Administrator role
- PowerShell 7.0 or later (for local development)
- Azure CLI installed
- Azure Functions Core Tools v4

## 🏗️ Architecture Overview

```
Azure AD Tenant → Azure Function (PowerShell) → CSV Report → Azure Blob Storage
     ↑                    ↑                                        ↓
Microsoft Graph API   Timer Trigger                        Public/Private URL
                    (Every Monday 1AM)
```

## 🚀 Step-by-Step Deployment Instructions

### Step 1: Create Azure Resources

#### 1.1 Create Resource Group
```bash
az group create --name "rg-inactive-users-report" --location "East US"
```

#### 1.2 Create Storage Account
```bash
az storage account create \
  --name "stinactiveusersreport" \
  --resource-group "rg-inactive-users-report" \
  --location "East US" \
  --sku "Standard_LRS" \
  --kind "StorageV2"
```

#### 1.3 Create Blob Container
```bash
az storage container create \
  --name "reports" \
  --account-name "stinactiveusersreport" \
  --public-access off
```

#### 1.4 Create Function App
```bash
az functionapp create \
  --resource-group "rg-inactive-users-report" \
  --consumption-plan-location "East US" \
  --runtime "powershell" \
  --runtime-version "7.2" \
  --functions-version "4" \
  --name "func-inactive-users-report" \
  --storage-account "stinactiveusersreport" \
  --disable-app-insights false
```

### Step 2: Create Azure AD App Registration

#### 2.1 Register Application
```bash
az ad app create \
  --display-name "Inactive Users Report Function" \
  --sign-in-audience "AzureADMyOrg"
```

#### 2.2 Create Service Principal
```bash
# Get the app ID from the previous command output
APP_ID="your-app-id-here"

az ad sp create --id $APP_ID
```

#### 2.3 Create Client Secret
```bash
az ad app credential reset --id $APP_ID --display-name "FunctionSecret"
```

**⚠️ Important:** Save the client secret value - you won't be able to retrieve it later!

#### 2.4 Grant Microsoft Graph Permissions

**Via Azure Portal (Recommended):**
1. Go to Azure Portal → Azure Active Directory → App registrations
2. Find your app "Inactive Users Report Function"
3. Go to "API permissions"
4. Click "Add a permission" → Microsoft Graph → Application permissions
5. Add these permissions:
   - `User.Read.All`
   - `AuditLog.Read.All`
   - `Directory.Read.All`
6. Click "Grant admin consent for [Your Tenant]"

**Via Azure CLI:**
```bash
# Get Microsoft Graph service principal ID
GRAPH_SP_ID=$(az ad sp list --display-name "Microsoft Graph" --query "[0].id" -o tsv)

# Grant permissions
az ad app permission add --id $APP_ID --api 00000003-0000-0000-c000-000000000000 --api-permissions df021288-bdef-4463-88db-98f22de89214=Role
az ad app permission add --id $APP_ID --api 00000003-0000-0000-c000-000000000000 --api-permissions b0afded3-3588-46d8-8b3d-9842eff778da=Role
az ad app permission add --id $APP_ID --api 00000003-0000-0000-c000-000000000000 --api-permissions 7ab1d382-f21e-4acd-a863-ba3e13f7da61=Role

# Grant admin consent
az ad app permission admin-consent --id $APP_ID
```

### Step 3: Configure Function App Settings

#### 3.1 Get Required Values
```bash
# Get tenant ID
TENANT_ID=$(az account show --query tenantId -o tsv)

# Get storage account key
STORAGE_KEY=$(az storage account keys list --resource-group "rg-inactive-users-report" --account-name "stinactiveusersreport" --query "[0].value" -o tsv)

echo "Tenant ID: $TENANT_ID"
echo "Storage Key: $STORAGE_KEY"
echo "App ID: $APP_ID"
echo "Client Secret: [Use the value from step 2.3]"
```

#### 3.2 Set Application Settings
```bash
az functionapp config appsettings set \
  --name "func-inactive-users-report" \
  --resource-group "rg-inactive-users-report" \
  --settings \
    "TENANT_ID=$TENANT_ID" \
    "CLIENT_ID=$APP_ID" \
    "CLIENT_SECRET=your-client-secret-from-step-2.3" \
    "STORAGE_ACCOUNT_NAME=stinactiveusersreport" \
    "STORAGE_ACCOUNT_KEY=$STORAGE_KEY" \
    "CONTAINER_NAME=reports"
```

### Step 4: Deploy Function Code

#### 4.1 Install Azure Functions Core Tools
```bash
# Windows (via npm)
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# macOS (via Homebrew)
brew tap azure/functions
brew install azure-functions-core-tools@4

# Linux (via package manager)
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-$(lsb_release -cs)-prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list'
sudo apt-get update
sudo apt-get install azure-functions-core-tools-4
```

#### 4.2 Deploy Function
```bash
# Navigate to your function directory
cd /path/to/your/function/code

# Deploy to Azure
func azure functionapp publish func-inactive-users-report
```

### Step 5: Test the Function

#### 5.1 Manual Test
```bash
# Trigger the function manually
az functionapp function invoke \
  --resource-group "rg-inactive-users-report" \
  --name "func-inactive-users-report" \
  --function-name "InactiveUsersReport"
```

#### 5.2 Check Logs
```bash
# View function logs
az functionapp log tail \
  --name "func-inactive-users-report" \
  --resource-group "rg-inactive-users-report"
```

#### 5.3 Verify Blob Storage
```bash
# List blobs in the reports container
az storage blob list \
  --container-name "reports" \
  --account-name "stinactiveusersreport" \
  --output table
```

## 🔧 Configuration Options

### Timer Schedule
The function runs every Monday at 1:00 AM UTC. To change this, modify the `schedule` in `function.json`:

```json
{
  "schedule": "0 0 1 * * MON"  // CRON expression: sec min hour day month dayOfWeek
}
```

**Common Schedule Examples:**
- Daily at 2 AM: `"0 0 2 * * *"`
- Every Sunday at midnight: `"0 0 0 * * SUN"`
- First day of every month at 1 AM: `"0 0 1 1 * *"`

### Inactive Period
To change the 30-day inactive period, modify line 54 in `run.ps1`:
```powershell
$cutoffDate = (Get-Date).AddDays(-30)  # Change -30 to your desired number of days
```

## 🔐 Security Best Practices

### 1. Use Azure Key Vault (Recommended)
Instead of storing secrets in application settings:

```bash
# Create Key Vault
az keyvault create \
  --name "kv-inactive-users-report" \
  --resource-group "rg-inactive-users-report" \
  --location "East US"

# Store client secret
az keyvault secret set \
  --vault-name "kv-inactive-users-report" \
  --name "ClientSecret" \
  --value "your-client-secret"

# Update function app to use Key Vault reference
az functionapp config appsettings set \
  --name "func-inactive-users-report" \
  --resource-group "rg-inactive-users-report" \
  --settings "CLIENT_SECRET=@Microsoft.KeyVault(VaultName=kv-inactive-users-report;SecretName=ClientSecret)"
```

### 2. Enable Managed Identity
```bash
# Enable system-assigned managed identity
az functionapp identity assign \
  --name "func-inactive-users-report" \
  --resource-group "rg-inactive-users-report"

# Grant Key Vault access to the managed identity
az keyvault set-policy \
  --name "kv-inactive-users-report" \
  --object-id "managed-identity-principal-id" \
  --secret-permissions get
```

### 3. Restrict Blob Access
```bash
# Create a SAS token for limited access
az storage container generate-sas \
  --name "reports" \
  --account-name "stinactiveusersreport" \
  --permissions r \
  --expiry "2024-12-31T23:59:59Z" \
  --output tsv
```

## 📊 Report Format

The generated CSV report includes these columns:
- **DisplayName**: User's display name
- **UserPrincipalName**: User's email/UPN
- **UserId**: Azure AD Object ID
- **AccountEnabled**: Whether the account is enabled
- **CreatedDateTime**: When the account was created
- **LastSignIn**: Last sign-in date and time
- **DaysSinceLastSignIn**: Number of days since last sign-in
- **ReportGeneratedDate**: When this report was generated

## 🔍 Monitoring and Troubleshooting

### Application Insights
```bash
# Enable Application Insights
az monitor app-insights component create \
  --app "func-inactive-users-report-insights" \
  --location "East US" \
  --resource-group "rg-inactive-users-report"

# Link to Function App
az functionapp config appsettings set \
  --name "func-inactive-users-report" \
  --resource-group "rg-inactive-users-report" \
  --settings "APPINSIGHTS_INSTRUMENTATIONKEY=your-instrumentation-key"
```

### Common Issues and Solutions

#### Issue: "Insufficient privileges to complete the operation"
**Solution:** Ensure the app registration has the correct Microsoft Graph permissions and admin consent has been granted.

#### Issue: "Storage account not found"
**Solution:** Verify the storage account name and key in the function app settings.

#### Issue: "Function timeout"
**Solution:** Increase the function timeout in `host.json` or consider using a Consumption plan with longer timeout limits.

#### Issue: "Module import errors"
**Solution:** Ensure all required PowerShell modules are listed in `requirements.psd1` and the function app has internet access to download them.

## 💰 Cost Estimation

**Monthly costs (approximate):**
- Function App (Consumption): $0-5 (depending on execution time)
- Storage Account: $1-3 (for blob storage)
- Application Insights: $0-2 (for basic monitoring)

**Total estimated monthly cost: $1-10**

## 🔄 Maintenance

### Regular Tasks
1. **Review permissions**: Ensure the app registration still has necessary permissions
2. **Monitor costs**: Check Azure billing for unexpected charges
3. **Update modules**: Keep PowerShell modules updated in `requirements.psd1`
4. **Review reports**: Periodically check generated reports for accuracy
5. **Rotate secrets**: Regularly rotate the client secret (recommended every 6-12 months)

### Updating the Function
```bash
# After making code changes, redeploy
func azure functionapp publish func-inactive-users-report --force
```

## 📞 Support

For issues with:
- **Azure Functions**: Check Azure documentation and support
- **Microsoft Graph**: Review Graph API documentation
- **PowerShell modules**: Check PowerShell Gallery for module-specific issues

## 🔗 Useful Links

- [Azure Functions PowerShell Developer Guide](https://docs.microsoft.com/en-us/azure/azure-functions/functions-reference-powershell)
- [Microsoft Graph PowerShell SDK](https://docs.microsoft.com/en-us/powershell/microsoftgraph/)
- [Azure Functions Timer Trigger](https://docs.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer)
- [Azure Blob Storage with PowerShell](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-powershell)
