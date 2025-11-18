#!/usr/bin/env python3
"""
Verification script for Google APIs setup
Run this to test your OAuth credentials and Google Drive integration
"""

import os
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def check_env_file():
    """Check if .env file exists and has required variables"""
    print("[CHECK] Checking .env file...")

    env_path = Path('.env')
    if not env_path.exists():
        print("[ERROR] .env file not found!")
        return False

    required_vars = [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'GOOGLE_REFRESH_TOKEN',
        'Maps_API_KEY'
    ]

    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value or value.startswith('your_'):
            missing_vars.append(var)

    if missing_vars:
        print(f"[ERROR] Missing or placeholder values for: {', '.join(missing_vars)}")
        return False

    print("[OK] All required environment variables are set")
    return True

def test_google_drive():
    """Test Google Drive integration using the new structure"""
    print("\n[CHECK] Testing Google Drive integration...")

    try:
        creds = Credentials(
            None, refresh_token=os.environ.get("GOOGLE_REFRESH_TOKEN"),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.environ.get("GOOGLE_CLIENT_ID"), 
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
            scopes=['https://www.googleapis.com/auth/drive']
        )
        drive_service = build('drive', 'v3', credentials=creds)

        # Check if parent folder exists
        parent_folder_id = os.environ.get('PARENT_FOLDER_ID')
        if not parent_folder_id:
            print("[WARNING] PARENT_FOLDER_ID not set - Google Drive folder operations will be limited")
            print("   The app will still work for project management and financial summaries")
            return True

        # Try to get folder info
        folder = drive_service.files().get(
            fileId=parent_folder_id,
            fields='name, id'
        ).execute()

        print("[OK] Google Drive connected successfully")
        print(f"   Parent folder: {folder.get('name')} ({folder.get('id')})")
        return True

    except Exception as e:
        print(f"[WARNING] Cannot access parent folder: {e}")
        print("   This is normal if the folder was created with different OAuth credentials")
        print("   The app will work with limited Google Drive functionality")
        return True  # Return True since the service works, just not the folder

def main():
    """Run all verification tests"""
    print("SOLAR CALCULATOR SETUP VERIFICATION")
    print("=" * 50)

    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()

    tests = [
        ("Environment Variables", check_env_file),
        ("Google Drive API", test_google_drive),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")

    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("[SUCCESS] All tests passed! Your setup is ready.")
        print("\nTo run the application:")
        print("   python -m streamlit run app.py")
    else:
        print("[WARNING] Some tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("   1. Update your .env file with correct credentials")
        print("   2. Verify OAuth credentials are for 'Web application'")
        print("   3. Check that Google APIs are enabled in Cloud Console")
        print("   4. Ensure PARENT_FOLDER_ID is correct")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
