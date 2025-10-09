#!/usr/bin/env python3
"""
Google Drive Authentication Diagnostic Tool
Run this to check if your credentials and token are valid
"""

import os
import sys
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def check_file_exists(filepath):
    """Check if a file exists and show its details"""
    path = Path(filepath)
    if path.exists():
        size = path.stat().st_size
        print(f"✅ Found: {filepath} ({size} bytes)")
        return True
    else:
        print(f"❌ Missing: {filepath}")
        return False

def check_credentials_file():
    """Check credentials.json file"""
    print("\n" + "="*60)
    print("1️⃣ CHECKING CREDENTIALS.JSON")
    print("="*60)
    
    if not check_file_exists('credentials.json'):
        print("\n❌ PROBLEM: credentials.json not found!")
        print("📋 You need to:")
        print("   1. Go to: https://console.cloud.google.com/apis/credentials")
        print("   2. Create OAuth 2.0 Client ID")
        print("   3. Download JSON file")
        print("   4. Rename it to 'credentials.json'")
        print("   5. Place it in your project root")
        return False
    
    # Try to parse it
    try:
        with open('credentials.json', 'r') as f:
            creds_data = json.load(f)
        
        # Check structure
        if 'installed' in creds_data:
            print("✅ Valid OAuth desktop app credentials")
            client_id = creds_data['installed'].get('client_id', 'N/A')
            print(f"   Client ID: {client_id[:30]}...")
            return True
        elif 'web' in creds_data:
            print("⚠️  Found 'web' credentials - should be 'installed' for desktop apps")
            return False
        else:
            print("❌ Invalid credentials format")
            return False
            
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return False

def check_token_file():
    """Check token.json file"""
    print("\n" + "="*60)
    print("2️⃣ CHECKING TOKEN.JSON")
    print("="*60)
    
    if not check_file_exists('token.json'):
        print("\n⚠️  token.json not found - you need to authenticate first")
        return None
    
    # Try to parse it
    try:
        with open('token.json', 'r') as f:
            token_data = json.load(f)
        
        print("✅ token.json is valid JSON")
        
        # Check for required fields
        required_fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'scopes']
        missing = [f for f in required_fields if f not in token_data]
        
        if missing:
            print(f"❌ Missing fields: {missing}")
            return None
        
        print("✅ All required fields present")
        print(f"   Scopes: {token_data.get('scopes', [])}")
        
        return token_data
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Error reading token: {e}")
        return None

def test_token_validity():
    """Test if the token actually works"""
    print("\n" + "="*60)
    print("3️⃣ TESTING TOKEN VALIDITY")
    print("="*60)
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    try:
        # Load credentials from token.json
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        print("✅ Loaded credentials from token.json")
        
        # Check if expired
        if creds.expired:
            print("⚠️  Token is EXPIRED")
            
            if creds.refresh_token:
                print("🔄 Attempting to refresh token...")
                try:
                    creds.refresh(Request())
                    print("✅ Token refreshed successfully!")
                    
                    # Save refreshed token
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                    print("💾 Saved refreshed token to token.json")
                    
                except Exception as e:
                    print(f"❌ Failed to refresh token: {e}")
                    print("\n🔧 SOLUTION: Delete token.json and re-authenticate")
                    return False
            else:
                print("❌ No refresh token available")
                print("\n🔧 SOLUTION: Delete token.json and re-authenticate")
                return False
        else:
            print("✅ Token is VALID (not expired)")
        
        # Try to use the credentials
        print("\n🧪 Testing actual Google Drive API access...")
        service = build('drive', 'v3', credentials=creds)
        
        # Try a simple API call
        results = service.files().list(pageSize=1, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        print("✅ Successfully connected to Google Drive API!")
        print(f"   API is working correctly")
        
        return True
        
    except FileNotFoundError:
        print("❌ token.json not found")
        return False
    except Exception as e:
        print(f"❌ Error testing token: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

def main():
    """Run all diagnostic checks"""
    print("\n" + "🔍 GOOGLE DRIVE AUTHENTICATION DIAGNOSTIC TOOL")
    print("="*60)
    
    # Check working directory
    print(f"\n📁 Working Directory: {os.getcwd()}")
    print(f"📁 Files in current directory:")
    for item in sorted(os.listdir('.')):
        if not item.startswith('.'):
            print(f"   - {item}")
    
    # Run checks
    creds_ok = check_credentials_file()
    token_data = check_token_file()
    
    if not creds_ok:
        print("\n" + "="*60)
        print("❌ DIAGNOSIS: Missing or invalid credentials.json")
        print("="*60)
        print("\n🔧 TO FIX:")
        print("1. Go to Google Cloud Console: https://console.cloud.google.com/apis/credentials")
        print("2. Create OAuth 2.0 Client ID (Type: Desktop app)")
        print("3. Download the JSON file")
        print("4. Rename it to 'credentials.json'")
        print("5. Upload to your project root (same folder as app.py)")
        return
    
    if token_data is None:
        print("\n" + "="*60)
        print("⚠️  DIAGNOSIS: Need to authenticate")
        print("="*60)
        print("\n🔧 TO FIX:")
        print("Run the authentication script:")
        print("   python utils/gdrive_uploader.py")
        return
    
    # Test if token works
    token_valid = test_token_validity()
    
    print("\n" + "="*60)
    print("📊 FINAL DIAGNOSIS")
    print("="*60)
    
    if token_valid:
        print("✅ Everything is working!")
        print("   Your Google Drive integration should work now.")
    else:
        print("❌ Token is invalid or expired")
        print("\n🔧 TO FIX:")
        print("1. Delete token.json")
        print("2. Run: python utils/gdrive_uploader.py")
        print("3. Complete the authentication flow")

if __name__ == "__main__":
    main()
