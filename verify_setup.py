#!/usr/bin/env python3
"""
Verification script for Google APIs setup
Run this to test your OAuth credentials and Google Drive integration
"""

import os
import sys
from pathlib import Path

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


def test_financial_summary():
    """Test financial summary generator"""
    print("\n[CHECK] Testing financial summary generator...")

    try:
        from financial_summary import financial_summary_generator

        if financial_summary_generator is None:
            print("[ERROR] Financial summary generator not available")
            return False

        print("[OK] Financial summary generator loaded successfully")
        return True

    except Exception as e:
        print(f"[ERROR] Financial summary test failed: {e}")
        return False

def main():
    """Run all verification tests"""
    print("SOLAR CALCULATOR SETUP VERIFICATION")
    print("=" * 50)

    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()

    tests = [
        ("Environment Variables", check_env_file),
        ("Financial Summary", test_financial_summary)
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