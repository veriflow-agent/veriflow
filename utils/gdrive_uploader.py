# utils/gdrive_uploader.py
"""
✅ FIXED Google Drive Uploader for Replit Environments

MAJOR FIX: Changed from run_console() to run_local_server() with proper fallback
"""

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import os
from pathlib import Path
import json
from typing import Optional
from loguru import logger

class GoogleDriveUploader:
    """
    ✅ FIXED: Upload files to Google Drive with proper Replit authentication

    Changes from previous version:
    - Uses run_local_server() with manual fallback instead of run_console()
    - Better error handling for authentication
    - Clearer user instructions
    """

    # Google Drive API scopes
    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self, credentials_path: str = 'credentials.json'):
        """
        Initialize the Google Drive uploader

        Args:
            credentials_path: Path to OAuth credentials JSON file
        """
        self.credentials_path = credentials_path
        self.token_path = 'token.json'
        self.service = None

        # Get folder ID from environment or use None (root)
        self.folder_id = os.getenv('GDRIVE_FOLDER_ID')

        if not self.folder_id:
            logger.warning("⚠️ GDRIVE_FOLDER_ID not set. Files will be uploaded to Drive root.")
            logger.info("💡 Set GDRIVE_FOLDER_ID in .env to upload to a specific folder")

        logger.info("🔧 Initializing Google Drive uploader")

    def authenticate(self) -> bool:
        """
        ✅ FIXED: Authenticate with Google Drive using proper OAuth flow

        Returns:
            True if authentication successful, False otherwise
        """
        creds = None

        # Load existing token if available
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(
                    self.token_path, 
                    self.SCOPES
                )
                logger.info("✅ Loaded existing credentials from token.json")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load token.json: {e}")
                creds = None

        # Refresh expired token
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("🔄 Refreshing expired credentials")
                creds.refresh(Request())
                logger.info("✅ Credentials refreshed successfully")
            except Exception as e:
                logger.error(f"❌ Failed to refresh credentials: {e}")
                creds = None

        # Need new authentication
        if not creds or not creds.valid:
            logger.info("🔐 Starting OAuth flow")

            if not os.path.exists(self.credentials_path):
                logger.error(f"❌ Credentials file not found: {self.credentials_path}")
                logger.info("📋 Get credentials from: https://console.cloud.google.com/apis/credentials")
                return False

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path,
                    self.SCOPES
                )

                # ✅ FIX: Use run_local_server() with proper settings for Replit
                logger.info("🔧 Attempting browser-based authentication")
                logger.info("=" * 60)
                logger.info("AUTHENTICATION STEPS:")
                logger.info("1. A browser window will open automatically")
                logger.info("2. If it doesn't open, copy the URL shown below")
                logger.info("3. Sign in to your Google account")
                logger.info("4. Grant the requested permissions")
                logger.info("5. You'll be redirected back automatically")
                logger.info("=" * 60)

                try:
                    # ✅ Try local server first (works in most cases)
                    creds = flow.run_local_server(
                        port=0,  # Use random available port
                        authorization_prompt_message='',
                        success_message='Authentication successful! You can close this window.',
                        open_browser=True
                    )
                    logger.info("✅ Browser authentication successful")

                except Exception as server_error:
                    # ✅ FALLBACK: Manual authorization for environments where browser doesn't work
                    logger.warning(f"⚠️ Browser authentication failed: {server_error}")
                    logger.info("🔄 Switching to manual authorization flow")
                    logger.info("=" * 60)
                    logger.info("MANUAL AUTHORIZATION REQUIRED:")
                    logger.info("1. Visit this URL in your browser:")

                    # Get authorization URL
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    print(f"\n{auth_url}\n")

                    logger.info("2. Sign in and grant permissions")
                    logger.info("3. After approval, you'll see an authorization code")
                    logger.info("4. Copy that code and paste it below")
                    logger.info("=" * 60)

                    code = input('Enter the authorization code: ').strip()
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                    logger.info("✅ Manual authorization successful")

                # Save credentials for future use
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"💾 Credentials saved to {self.token_path}")

            except Exception as e:
                logger.error(f"❌ Authentication failed: {e}")
                return False

        # Initialize Google Drive service
        try:
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("✅ Google Drive service initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Drive service: {e}")
            return False

    def upload_file(
        self, 
        file_path: str, 
        drive_filename: Optional[str] = None,
        mime_type: str = 'text/plain'
    ) -> Optional[str]:
        """
        Upload a file to Google Drive

        Args:
            file_path: Path to the file to upload
            drive_filename: Name to use in Google Drive (defaults to original filename)
            mime_type: MIME type of the file

        Returns:
            File ID if successful, None otherwise
        """
        if not self.service:
            logger.error("❌ Not authenticated. Call authenticate() first.")
            return None

        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"❌ File not found: {file_path}")
            return None

        if not drive_filename:
            drive_filename = file_path.name

        logger.info(f"📤 Uploading: {file_path.name} → {drive_filename}")

        try:
            # File metadata
            file_metadata = {
                'name': drive_filename,
            }

            # Add folder if specified
            if self.folder_id:
                file_metadata['parents'] = [self.folder_id]
                logger.info(f"📁 Uploading to folder ID: {self.folder_id}")

            # Upload the file
            media = MediaFileUpload(
                str(file_path),
                mimetype=mime_type,
                resumable=True
            )

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()

            file_id = file.get('id')
            web_link = file.get('webViewLink')

            logger.info(f"✅ Upload successful!")
            logger.info(f"📄 File: {file.get('name')}")
            logger.info(f"🔗 ID: {file_id}")
            logger.info(f"🌐 Link: {web_link}")

            return file_id

        except HttpError as error:
            logger.error(f"❌ Upload failed: {error}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error during upload: {e}")
            return None

    def list_files(self, max_results: int = 10) -> list:
        """
        List files in Google Drive

        Args:
            max_results: Maximum number of files to return

        Returns:
            List of file dictionaries
        """
        if not self.service:
            logger.error("❌ Not authenticated. Call authenticate() first.")
            return []

        try:
            # Build query
            query_parts = []
            if self.folder_id:
                query_parts.append(f"'{self.folder_id}' in parents")
            query_parts.append("trashed=false")

            query = " and ".join(query_parts)

            results = self.service.files().list(
                pageSize=max_results,
                q=query,
                fields="files(id, name, createdTime, modifiedTime, size, webViewLink)"
            ).execute()

            files = results.get('files', [])

            if not files:
                logger.info('📂 No files found')
                return []

            logger.info(f'📂 Found {len(files)} files:')
            for file in files:
                size_mb = int(file.get('size', 0)) / (1024 * 1024) if file.get('size') else 0
                logger.info(f"  • {file['name']} ({size_mb:.2f} MB) - {file['id']}")

            return files

        except HttpError as error:
            logger.error(f"❌ Failed to list files: {error}")
            return []


# ✅ USAGE EXAMPLES
def example_authentication():
    """Example: How to authenticate"""
    uploader = GoogleDriveUploader()

    if uploader.authenticate():
        print("✅ Authentication successful!")
        return uploader
    else:
        print("❌ Authentication failed")
        return None


def example_upload_session_file():
    """Example: Upload a fact-check session file"""
    uploader = GoogleDriveUploader()

    # Authenticate first
    if not uploader.authenticate():
        print("❌ Authentication failed")
        return

    # Upload a session file
    session_file = "temp/20250929_150000/session_report.txt"

    file_id = uploader.upload_file(
        file_path=session_file,
        drive_filename="fact_check_session_20250929.txt",
        mime_type="text/plain"
    )

    if file_id:
        print(f"✅ File uploaded successfully! ID: {file_id}")
    else:
        print("❌ Upload failed")


def example_list_uploaded_files():
    """Example: List uploaded files"""
    uploader = GoogleDriveUploader()

    if not uploader.authenticate():
        print("❌ Authentication failed")
        return

    files = uploader.list_files(max_results=20)
    print(f"\n📂 Found {len(files)} files in Google Drive")


if __name__ == "__main__":
    # Run authentication test
    print("🧪 Testing Google Drive Authentication\n")
    uploader = example_authentication()

    if uploader:
        print("\n📂 Listing files in Drive...")
        uploader.list_files()