# Azure Inactive Users Scanner - Deployment Script
# This script automates the deployment of the Azure Function

param(
    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "rg-inactive-users-scanner",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [string]$FunctionAppName = "func-inactive-users-$((Get-Date).ToString('yyyyMMddHHmmss'))",
    
    [Parameter(Mandatory=$false)]
    [string]$StorageAccountName = "stinactiveusers$((Get-Date).ToString('yyyyMMddHHmmss'))",
    
    [Parameter(Mandatory=$false)]
    [string]$AppRegistrationName = "Inactive Users Scanner"
)

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "Starting deployment of Azure Inactive Users Scanner..." -ForegroundColor Green

# Login and set subscription
Write-Host "Setting Azure subscription..." -ForegroundColor Yellow
az account set --subscription $SubscriptionId

# Create resource group
Write-Host "Creating resource group: $ResourceGroupName" -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location

# Create storage account
Write-Host "Creating storage account: $StorageAccountName" -ForegroundColor Yellow
az storage account create `
    --name $StorageAccountName `
    --resource-group $ResourceGroupName `
    --location $Location `
    --sku Standard_LRS

# Create function app
Write-Host "Creating function app: $FunctionAppName" -ForegroundColor Yellow
az functionapp create `
    --resource-group $ResourceGroupName `
    --consumption-plan-location $Location `
    --runtime python `
    --runtime-version 3.9 `
    --functions-version 4 `
    --name $FunctionAppName `
    --storage-account $StorageAccountName

# Create Azure AD app registration
Write-Host "Creating Azure AD app registration..." -ForegroundColor Yellow
$appRegistration = az ad app create --display-name $AppRegistrationName --sign-in-audience AzureADMyOrg | ConvertFrom-Json
$clientId = $appRegistration.appId

Write-Host "App Registration created with Client ID: $clientId" -ForegroundColor Green

# Create service principal
Write-Host "Creating service principal..." -ForegroundColor Yellow
az ad sp create --id $clientId

# Create client secret
Write-Host "Creating client secret..." -ForegroundColor Yellow
$secretResult = az ad app credential reset --id $clientId --display-name "Function App Secret" | ConvertFrom-Json
$clientSecret = $secretResult.password

Write-Host "Client secret created successfully" -ForegroundColor Green

# Grant API permissions
Write-Host "Granting Microsoft Graph API permissions..." -ForegroundColor Yellow
$graphAppId = "00000003-0000-0000-c000-000000000000"

# Grant User.Read.All permission
az ad app permission add --id $clientId --api $graphAppId --api-permissions "df021288-bdef-4463-88db-98f22de89214=Role"

# Grant AuditLog.Read.All permission
az ad app permission add --id $clientId --api $graphAppId --api-permissions "b0afded3-3588-46d8-8b3d-9842eff778da=Role"

# Grant admin consent
Write-Host "Granting admin consent..." -ForegroundColor Yellow
az ad app permission admin-consent --id $clientId

# Get tenant ID
$tenantId = az account show --query tenantId -o tsv

# Get storage connection string
$storageConnectionString = az storage account show-connection-string --name $StorageAccountName --resource-group $ResourceGroupName --query connectionString -o tsv

# Configure function app settings
Write-Host "Configuring function app settings..." -ForegroundColor Yellow
az functionapp config appsettings set `
    --name $FunctionAppName `
    --resource-group $ResourceGroupName `
    --settings `
        "TENANT_ID=$tenantId" `
        "CLIENT_ID=$clientId" `
        "CLIENT_SECRET=$clientSecret" `
        "STORAGE_CONNECTION_STRING=$storageConnectionString" `
        "BLOB_CONTAINER_NAME=inactive-users-reports"

# Create blob container
Write-Host "Creating blob storage container..." -ForegroundColor Yellow
az storage container create --name "inactive-users-reports" --account-name $StorageAccountName --auth-mode login

# Deploy function code
Write-Host "Deploying function code..." -ForegroundColor Yellow
if (Test-Path "function-app.zip") {
    Remove-Item "function-app.zip"
}

# Create deployment package
Compress-Archive -Path ".\*" -DestinationPath "function-app.zip" -Exclude @("*.git*", "*.vscode*", "__pycache__*", "*.pyc", "deploy.ps1", "function-app.zip")

# Deploy to Azure
az functionapp deployment source config-zip --resource-group $ResourceGroupName --name $FunctionAppName --src "function-app.zip"

# Clean up deployment package
Remove-Item "function-app.zip"

Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
Write-Host "`nDeployment Summary:" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "Function App: $FunctionAppName" -ForegroundColor White
Write-Host "Storage Account: $StorageAccountName" -ForegroundColor White
Write-Host "Client ID: $clientId" -ForegroundColor White
Write-Host "Tenant ID: $tenantId" -ForegroundColor White
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Test the function in Azure Portal" -ForegroundColor White
Write-Host "2. Monitor logs for any issues" -ForegroundColor White
Write-Host "3. Verify blob storage container is created" -ForegroundColor White
Write-Host "4. Check that the function runs on schedule (Mondays at 1 AM EST)" -ForegroundColor White

Write-Host "`nIMPORTANT: Store the Client Secret securely!" -ForegroundColor Red
Write-Host "Client Secret: $clientSecret" -ForegroundColor Red

