# Azure Inactive Users Scanner Function

This Azure Function automatically scans for inactive users in your Azure Enterprise ID and generates CSV reports stored in Azure Blob Storage.

## Features

- **Scheduled Execution**: Runs every Monday at 1:00 AM EST (6:00 AM UTC)
- **Inactive User Detection**: Identifies users who haven't logged in for the past 60 days
- **Comprehensive Data Collection**: Captures username, user principal name, user principal ID, last login date, and days since last login
- **CSV Export**: Generates well-formatted CSV reports
- **Azure Blob Storage**: Automatically uploads reports to blob storage with timestamps
- **Error Handling**: Robust error handling and logging

## Prerequisites

1. **Azure Function App** with Python 3.9+ runtime
2. **Azure AD App Registration** with the following permissions:
   - `User.Read.All` (Application permission)
   - `AuditLog.Read.All` (Application permission)
3. **Azure Storage Account** for blob storage
4. **Admin Consent** granted for the app registration

## Setup Instructions

### 1. Azure AD App Registration

1. Go to Azure Portal > Azure Active Directory > App registrations
2. Click "New registration"
3. Provide a name (e.g., "Inactive Users Scanner")
4. Select "Accounts in this organizational directory only"
5. Click "Register"

### 2. Configure API Permissions

1. In your app registration, go to "API permissions"
2. Click "Add a permission" > "Microsoft Graph" > "Application permissions"
3. Add the following permissions:
   - `User.Read.All`
   - `AuditLog.Read.All`
4. Click "Grant admin consent"

### 3. Create Client Secret

1. Go to "Certificates & secrets"
2. Click "New client secret"
3. Provide a description and expiration period
4. Copy the secret value (you won't be able to see it again)

### 4. Configure Environment Variables

Set the following environment variables in your Azure Function App:

```
TENANT_ID=your-azure-tenant-id
CLIENT_ID=your-app-registration-client-id
CLIENT_SECRET=your-client-secret
STORAGE_CONNECTION_STRING=your-storage-account-connection-string
BLOB_CONTAINER_NAME=inactive-users-reports
```

### 5. Deploy the Function

1. Install Azure Functions Core Tools
2. Deploy using Azure CLI or VS Code Azure Functions extension

```bash
# Using Azure CLI
az functionapp deployment source config-zip \
  --resource-group your-resource-group \
  --name your-function-app-name \
  --src function-app.zip
```

## Schedule Configuration

The function is configured to run every Monday at 1:00 AM EST using the CRON expression:
```
0 0 6 * * 1
```

This translates to:
- `0` seconds
- `0` minutes  
- `6` hours (1:00 AM EST = 6:00 AM UTC)
- `*` any day of month
- `*` any month
- `1` Monday (0=Sunday, 1=Monday, etc.)

## Output Format

The generated CSV file contains the following columns:

| Column | Description |
|--------|-------------|
| username | Display name of the user |
| userPrincipalName | User's principal name (email) |
| userPrincipalId | Unique identifier for the user |
| lastLoginDate | Date and time of last login (UTC) |
| daysSinceLastLogin | Number of days since last login |

## File Naming Convention

CSV files are stored in blob storage with the following naming pattern:
```
inactive_users_report_YYYYMMDD_HHMMSS.csv
```

Example: `inactive_users_report_20241201_060000.csv`

## Monitoring and Troubleshooting

### Logs

Monitor function execution through:
- Azure Portal > Function App > Functions > InactiveUsersScanner > Monitor
- Application Insights (if configured)

### Common Issues

1. **Permission Errors**: Ensure admin consent is granted for API permissions
2. **Token Acquisition Failures**: Verify tenant ID, client ID, and client secret
3. **Storage Errors**: Check storage connection string and container permissions
4. **Rate Limiting**: Microsoft Graph API has rate limits; the function includes appropriate handling

### Testing

To test the function manually:
1. Go to Azure Portal > Function App > Functions > InactiveUsersScanner
2. Click "Test/Run"
3. Click "Run" to execute immediately

## Security Considerations

- Store all sensitive configuration in Azure Key Vault (recommended)
- Regularly rotate client secrets
- Monitor function execution logs for any security issues
- Ensure blob storage has appropriate access controls

## Cost Optimization

- Function runs once per week, minimizing compute costs
- Uses efficient Graph API queries with pagination
- Stores only necessary data in CSV format

## Compliance

This function helps with:
- Security auditing
- Compliance reporting
- User lifecycle management
- License optimization

## Support

For issues or questions:
1. Check Azure Function logs
2. Verify API permissions and consent
3. Test Graph API access manually
4. Review storage account configuration

