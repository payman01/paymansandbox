# Azure Inactive Users Report Function

🔍 **Automated Azure AD user activity monitoring with PowerShell Azure Functions**

This solution automatically generates weekly reports of users who haven't logged into your Azure AD tenant in the past 30 days. Reports are saved as CSV files in Azure Blob Storage with accessible URLs.

## ✨ Features

- 🕐 **Automated Scheduling**: Runs every Monday at 1:00 AM UTC
- 📊 **Comprehensive Reporting**: Tracks both interactive and non-interactive sign-ins
- 🔐 **Secure Authentication**: Uses Azure AD app registration with Microsoft Graph API
- 💾 **Cloud Storage**: Automatically saves reports to Azure Blob Storage
- 📈 **Detailed Metrics**: Includes user details, last sign-in dates, and inactive periods
- 🔍 **Monitoring Ready**: Built-in logging and Application Insights support

## 📋 What's Included

```
📁 Project Structure
├── InactiveUsersReport/
│   ├── run.ps1              # Main PowerShell function
│   └── function.json        # Timer trigger configuration
├── requirements.psd1        # PowerShell module dependencies
├── host.json               # Function app configuration
├── profile.ps1             # PowerShell profile for cold starts
├── local.settings.json     # Local development settings
├── DEPLOYMENT_GUIDE.md     # Complete deployment instructions
└── README.md              # This file
```

## 🚀 Quick Start

1. **Prerequisites**: Azure subscription, Azure AD admin rights, Azure CLI
2. **Deploy Resources**: Follow the [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for step-by-step instructions
3. **Configure Permissions**: Set up Azure AD app registration with Microsoft Graph permissions
4. **Deploy Function**: Use Azure Functions Core Tools to deploy the code
5. **Test & Monitor**: Verify the function runs and generates reports

## 📊 Report Output

The generated CSV report includes:

| Column | Description |
|--------|-------------|
| DisplayName | User's display name |
| UserPrincipalName | User's email/UPN |
| UserId | Azure AD Object ID |
| AccountEnabled | Account status |
| CreatedDateTime | Account creation date |
| LastSignIn | Most recent sign-in |
| DaysSinceLastSignIn | Days since last activity |
| ReportGeneratedDate | Report timestamp |

## ⚙️ Configuration

### Schedule Modification
Edit `InactiveUsersReport/function.json` to change the schedule:
```json
{
  "schedule": "0 0 1 * * MON"  // Every Monday at 1 AM UTC
}
```

### Inactive Period
Modify the cutoff period in `InactiveUsersReport/run.ps1`:
```powershell
$cutoffDate = (Get-Date).AddDays(-30)  // Change -30 to desired days
```

## 🔐 Security Features

- **Azure AD App Registration**: Secure service principal authentication
- **Microsoft Graph API**: Official Microsoft APIs for user data
- **Key Vault Integration**: Optional secure secret storage
- **Managed Identity**: Azure-native authentication
- **Private Blob Storage**: Controlled access to reports

## 💰 Cost Estimate

**Monthly costs (approximate):**
- Azure Function (Consumption): $0-5
- Blob Storage: $1-3
- Application Insights: $0-2

**Total: $1-10/month**

## 🔧 Customization Options

- **Multiple Tenants**: Extend to support multiple Azure AD tenants
- **Email Notifications**: Add email alerts for high inactive user counts
- **Custom Filters**: Filter by department, location, or user attributes
- **Different Formats**: Export to Excel, JSON, or other formats
- **Integration**: Connect with ITSM tools or HR systems

## 📖 Documentation

- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)**: Complete deployment instructions
- **[Azure Functions Docs](https://docs.microsoft.com/en-us/azure/azure-functions/)**
- **[Microsoft Graph PowerShell](https://docs.microsoft.com/en-us/powershell/microsoftgraph/)**

## 🐛 Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure Microsoft Graph permissions are granted and admin consent is provided
2. **Storage Errors**: Verify storage account credentials and container exists
3. **Module Errors**: Check `requirements.psd1` for correct module versions
4. **Timeout Issues**: Increase function timeout in `host.json`

### Getting Help

- Check Azure Function logs in the Azure Portal
- Review Application Insights for detailed telemetry
- Verify environment variables are set correctly
- Test Microsoft Graph connectivity manually

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve this solution!

## 📄 License

This project is provided as-is for educational and operational purposes. Please review and comply with your organization's security and compliance requirements before deployment.

---

**⚡ Ready to deploy?** Check out the [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for complete step-by-step instructions!
