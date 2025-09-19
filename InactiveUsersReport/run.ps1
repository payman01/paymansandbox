# Azure Function to generate inactive users report
# Runs every Monday at 1AM to scan user logins and create CSV report

using namespace System.Net

# Input bindings are passed in via param block.
param($Timer)

# Import required modules
Import-Module Az.Accounts -Force
Import-Module Az.Storage -Force
Import-Module Microsoft.Graph.Authentication -Force
Import-Module Microsoft.Graph.Users -Force
Import-Module Microsoft.Graph.Reports -Force

# Function to write logs
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Output "[$timestamp] [$Level] $Message"
}

try {
    Write-Log "Starting Inactive Users Report generation..."
    
    # Get environment variables
    $tenantId = $env:TENANT_ID
    $clientId = $env:CLIENT_ID
    $clientSecret = $env:CLIENT_SECRET
    $storageAccountName = $env:STORAGE_ACCOUNT_NAME
    $storageAccountKey = $env:STORAGE_ACCOUNT_KEY
    $containerName = $env:CONTAINER_NAME
    
    if (-not $tenantId -or -not $clientId -or -not $clientSecret) {
        throw "Missing required environment variables: TENANT_ID, CLIENT_ID, or CLIENT_SECRET"
    }
    
    if (-not $storageAccountName -or -not $storageAccountKey -or -not $containerName) {
        throw "Missing required storage environment variables: STORAGE_ACCOUNT_NAME, STORAGE_ACCOUNT_KEY, or CONTAINER_NAME"
    }
    
    Write-Log "Environment variables loaded successfully"
    
    # Connect to Microsoft Graph
    $secureClientSecret = ConvertTo-SecureString $clientSecret -AsPlainText -Force
    $credential = New-Object System.Management.Automation.PSCredential($clientId, $secureClientSecret)
    
    Write-Log "Connecting to Microsoft Graph..."
    Connect-MgGraph -TenantId $tenantId -ClientSecretCredential $credential -NoWelcome
    
    Write-Log "Successfully connected to Microsoft Graph"
    
    # Calculate date 30 days ago
    $cutoffDate = (Get-Date).AddDays(-30)
    Write-Log "Checking for users inactive since: $($cutoffDate.ToString('yyyy-MM-dd'))"
    
    # Get all users
    Write-Log "Retrieving all users from tenant..."
    $allUsers = Get-MgUser -All -Property "Id,DisplayName,UserPrincipalName,AccountEnabled,CreatedDateTime,SignInActivity"
    
    Write-Log "Found $($allUsers.Count) total users"
    
    # Filter inactive users
    $inactiveUsers = @()
    
    foreach ($user in $allUsers) {
        $isInactive = $false
        $lastSignIn = "Never"
        $daysSinceLastSignIn = "N/A"
        
        if ($user.AccountEnabled -eq $false) {
            # Skip disabled accounts
            continue
        }
        
        if ($user.SignInActivity) {
            $lastInteractiveSignIn = $user.SignInActivity.LastSignInDateTime
            $lastNonInteractiveSignIn = $user.SignInActivity.LastNonInteractiveSignInDateTime
            
            # Get the most recent sign-in
            $mostRecentSignIn = $null
            if ($lastInteractiveSignIn -and $lastNonInteractiveSignIn) {
                $mostRecentSignIn = if ($lastInteractiveSignIn -gt $lastNonInteractiveSignIn) { $lastInteractiveSignIn } else { $lastNonInteractiveSignIn }
            } elseif ($lastInteractiveSignIn) {
                $mostRecentSignIn = $lastInteractiveSignIn
            } elseif ($lastNonInteractiveSignIn) {
                $mostRecentSignIn = $lastNonInteractiveSignIn
            }
            
            if ($mostRecentSignIn) {
                $lastSignInDate = [DateTime]::Parse($mostRecentSignIn)
                $lastSignIn = $lastSignInDate.ToString('yyyy-MM-dd HH:mm:ss')
                $daysSinceLastSignIn = [math]::Round((Get-Date - $lastSignInDate).TotalDays)
                
                if ($lastSignInDate -lt $cutoffDate) {
                    $isInactive = $true
                }
            } else {
                $isInactive = $true
            }
        } else {
            $isInactive = $true
        }
        
        if ($isInactive) {
            $inactiveUsers += [PSCustomObject]@{
                DisplayName = $user.DisplayName
                UserPrincipalName = $user.UserPrincipalName
                UserId = $user.Id
                AccountEnabled = $user.AccountEnabled
                CreatedDateTime = if ($user.CreatedDateTime) { ([DateTime]::Parse($user.CreatedDateTime)).ToString('yyyy-MM-dd HH:mm:ss') } else { "Unknown" }
                LastSignIn = $lastSignIn
                DaysSinceLastSignIn = $daysSinceLastSignIn
                ReportGeneratedDate = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
            }
        }
    }
    
    Write-Log "Found $($inactiveUsers.Count) inactive users (not signed in for 30+ days)"
    
    # Generate CSV content
    $csvContent = $inactiveUsers | ConvertTo-Csv -NoTypeInformation
    
    # Create filename with timestamp
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $fileName = "inactive_users_report_$timestamp.csv"
    
    Write-Log "Generated CSV report: $fileName"
    
    # Upload to Azure Blob Storage
    Write-Log "Uploading report to Azure Blob Storage..."
    
    # Create storage context
    $storageContext = New-AzStorageContext -StorageAccountName $storageAccountName -StorageAccountKey $storageAccountKey
    
    # Create temporary file for upload
    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        # Write CSV content to temporary file
        $csvContent | Out-File -FilePath $tempFile -Encoding UTF8
        
        # Upload blob from file
        $blob = Set-AzStorageBlobContent -File $tempFile -Container $containerName -Blob $fileName -BlobType Block -Context $storageContext -Force
        
    } finally {
        # Clean up temporary file
        if (Test-Path $tempFile) {
            Remove-Item $tempFile -Force
        }
    }
    
    if ($blob) {
        # Generate blob URL
        $blobUrl = "https://$storageAccountName.blob.core.windows.net/$containerName/$fileName"
        
        Write-Log "Report successfully uploaded to: $blobUrl"
        Write-Log "Report contains $($inactiveUsers.Count) inactive users"
        
        # Create summary for function output
        $summary = @{
            Status = "Success"
            ReportUrl = $blobUrl
            FileName = $fileName
            InactiveUsersCount = $inactiveUsers.Count
            TotalUsersScanned = $allUsers.Count
            GeneratedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
            CutoffDate = $cutoffDate.ToString('yyyy-MM-dd')
        }
        
        Write-Log "Function completed successfully"
        Write-Output $summary | ConvertTo-Json -Depth 3
        
    } else {
        throw "Failed to upload blob to storage account"
    }
    
} catch {
    $errorMessage = $_.Exception.Message
    Write-Log "ERROR: $errorMessage" -Level "ERROR"
    Write-Log "Stack Trace: $($_.ScriptStackTrace)" -Level "ERROR"
    
    # Return error response
    $errorResponse = @{
        Status = "Error"
        ErrorMessage = $errorMessage
        Timestamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    }
    
    Write-Output $errorResponse | ConvertTo-Json -Depth 3
    throw
} finally {
    # Disconnect from Microsoft Graph
    try {
        Disconnect-MgGraph -ErrorAction SilentlyContinue
        Write-Log "Disconnected from Microsoft Graph"
    } catch {
        Write-Log "Warning: Could not disconnect from Microsoft Graph: $($_.Exception.Message)" -Level "WARN"
    }
}
