import datetime
import logging
import os
import csv
import io
from typing import List, Dict, Any
import azure.functions as func
import msal
import requests
import pandas as pd
from azure.storage.blob import BlobServiceClient
from dateutil import parser, tz


def main(mytimer: func.TimerRequest) -> None:
    """
    Azure Function that runs every Monday at 1:00 AM EST to scan for inactive users.
    Collects users who haven't logged in for the past 60 days and stores the data in CSV format in blob storage.
    """
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    
    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info(f'Python timer trigger function ran at {utc_timestamp}')
    
    try:
        # Initialize the scanner
        scanner = InactiveUsersScanner()
        
        # Get inactive users
        inactive_users = scanner.get_inactive_users()
        
        if inactive_users:
            # Generate CSV and upload to blob storage
            csv_content = scanner.generate_csv(inactive_users)
            blob_name = scanner.upload_to_blob_storage(csv_content)
            
            logging.info(f'Successfully processed {len(inactive_users)} inactive users and uploaded to blob: {blob_name}')
        else:
            logging.info('No inactive users found.')
            
    except Exception as e:
        logging.error(f'Error in main function: {str(e)}')
        raise


class InactiveUsersScanner:
    """Class to handle scanning for inactive users and uploading results to blob storage."""
    
    def __init__(self):
        """Initialize the scanner with configuration from environment variables."""
        self.tenant_id = os.environ.get('TENANT_ID')
        self.client_id = os.environ.get('CLIENT_ID')
        self.client_secret = os.environ.get('CLIENT_SECRET')
        self.storage_connection_string = os.environ.get('STORAGE_CONNECTION_STRING')
        self.blob_container_name = os.environ.get('BLOB_CONTAINER_NAME', 'inactive-users-reports')
        
        # Validate required environment variables
        if not all([self.tenant_id, self.client_id, self.client_secret, self.storage_connection_string]):
            raise ValueError("Missing required environment variables. Please check TENANT_ID, CLIENT_ID, CLIENT_SECRET, and STORAGE_CONNECTION_STRING.")
        
        self.graph_endpoint = 'https://graph.microsoft.com/v1.0'
        self.scope = ['https://graph.microsoft.com/.default']
        
        # Calculate the cutoff date (60 days ago)
        self.cutoff_date = datetime.datetime.now(tz.UTC) - datetime.timedelta(days=60)
        
    def get_access_token(self) -> str:
        """Get access token for Microsoft Graph API using client credentials flow."""
        try:
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                client_credential=self.client_secret,
            )
            
            result = app.acquire_token_silent(self.scope, account=None)
            
            if not result:
                result = app.acquire_token_for_client(scopes=self.scope)
            
            if "access_token" in result:
                return result["access_token"]
            else:
                raise Exception(f"Failed to acquire token: {result.get('error_description', 'Unknown error')}")
                
        except Exception as e:
            logging.error(f"Error acquiring access token: {str(e)}")
            raise
    
    def get_all_users(self, access_token: str) -> List[Dict[str, Any]]:
        """Get all users from Azure AD."""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        all_users = []
        url = f"{self.graph_endpoint}/users"
        
        # Add select parameter to get only required fields
        params = {
            '$select': 'id,userPrincipalName,displayName,signInActivity,accountEnabled',
            '$top': 999  # Maximum page size
        }
        
        try:
            while url:
                response = requests.get(url, headers=headers, params=params if url == f"{self.graph_endpoint}/users" else None)
                response.raise_for_status()
                
                data = response.json()
                all_users.extend(data.get('value', []))
                
                # Get next page URL
                url = data.get('@odata.nextLink')
                params = None  # Clear params for subsequent requests
                
                logging.info(f"Retrieved {len(all_users)} users so far...")
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching users: {str(e)}")
            raise
            
        logging.info(f"Total users retrieved: {len(all_users)}")
        return all_users
    
    def get_inactive_users(self) -> List[Dict[str, Any]]:
        """Get users who haven't logged in for the past 60 days."""
        try:
            access_token = self.get_access_token()
            all_users = self.get_all_users(access_token)
            
            inactive_users = []
            
            for user in all_users:
                # Skip disabled accounts
                if not user.get('accountEnabled', True):
                    continue
                    
                # Check sign-in activity
                sign_in_activity = user.get('signInActivity', {})
                last_sign_in = sign_in_activity.get('lastSignInDateTime')
                
                # If no sign-in activity recorded, consider as inactive
                if not last_sign_in:
                    inactive_users.append({
                        'username': user.get('displayName', 'N/A'),
                        'userPrincipalName': user.get('userPrincipalName', 'N/A'),
                        'userPrincipalId': user.get('id', 'N/A'),
                        'lastLoginDate': 'Never logged in',
                        'daysSinceLastLogin': 'N/A'
                    })
                else:
                    # Parse the last sign-in date
                    try:
                        last_login_date = parser.isoparse(last_sign_in)
                        
                        # Check if the last login was before the cutoff date
                        if last_login_date < self.cutoff_date:
                            days_since_login = (datetime.datetime.now(tz.UTC) - last_login_date).days
                            
                            inactive_users.append({
                                'username': user.get('displayName', 'N/A'),
                                'userPrincipalName': user.get('userPrincipalName', 'N/A'),
                                'userPrincipalId': user.get('id', 'N/A'),
                                'lastLoginDate': last_login_date.strftime('%Y-%m-%d %H:%M:%S UTC'),
                                'daysSinceLastLogin': days_since_login
                            })
                    except Exception as e:
                        logging.warning(f"Error parsing date for user {user.get('userPrincipalName')}: {str(e)}")
                        continue
            
            logging.info(f"Found {len(inactive_users)} inactive users out of {len(all_users)} total users")
            return inactive_users
            
        except Exception as e:
            logging.error(f"Error getting inactive users: {str(e)}")
            raise
    
    def generate_csv(self, inactive_users: List[Dict[str, Any]]) -> str:
        """Generate CSV content from inactive users data."""
        try:
            # Create DataFrame
            df = pd.DataFrame(inactive_users)
            
            # Sort by days since last login (descending)
            if 'daysSinceLastLogin' in df.columns:
                # Handle 'N/A' values for sorting
                df['sortKey'] = df['daysSinceLastLogin'].apply(lambda x: 999999 if x == 'N/A' else x)
                df = df.sort_values('sortKey', ascending=False).drop('sortKey', axis=1)
            
            # Generate CSV content
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, quoting=csv.QUOTE_ALL)
            csv_content = csv_buffer.getvalue()
            csv_buffer.close()
            
            return csv_content
            
        except Exception as e:
            logging.error(f"Error generating CSV: {str(e)}")
            raise
    
    def upload_to_blob_storage(self, csv_content: str) -> str:
        """Upload CSV content to Azure Blob Storage."""
        try:
            # Create blob service client
            blob_service_client = BlobServiceClient.from_connection_string(self.storage_connection_string)
            
            # Generate blob name with timestamp
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            blob_name = f"inactive_users_report_{timestamp}.csv"
            
            # Create container if it doesn't exist
            try:
                container_client = blob_service_client.get_container_client(self.blob_container_name)
                container_client.create_container()
                logging.info(f"Created container: {self.blob_container_name}")
            except Exception:
                # Container already exists
                pass
            
            # Upload the CSV content
            blob_client = blob_service_client.get_blob_client(
                container=self.blob_container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(csv_content, overwrite=True)
            
            logging.info(f"Successfully uploaded CSV to blob: {blob_name}")
            return blob_name
            
        except Exception as e:
            logging.error(f"Error uploading to blob storage: {str(e)}")
            raise

