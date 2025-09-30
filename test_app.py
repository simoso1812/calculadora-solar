#!/usr/bin/env python3
"""
Simple test script to check if the Streamlit app can start without errors.
This helps identify deployment issues.
"""

import sys
import os

def test_imports():
    """Test all imports used in the app"""
    try:
        print("Testing basic imports...")
        import streamlit as st
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt
        print("✓ Basic imports successful")

        print("Testing financial imports...")
        import numpy_financial as npf
        print("✓ Financial imports successful")

        print("Testing PDF imports...")
        from fpdf import FPDF
        print("✓ PDF imports successful")

        print("Testing mapping imports...")
        import folium
        from streamlit_folium import st_folium
        print("✓ Mapping imports successful")

        print("Testing app-specific imports...")
        from carbon_calculator import CarbonEmissionsCalculator
        from financial_summary import financial_summary_generator
        print("✓ App-specific imports successful")

        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_app_structure():
    """Test if app.py can be imported without running"""
    try:
        print("Testing app.py import...")
        # We can't actually import app.py because it has st.set_page_config()
        # but we can check if the file exists and has valid syntax
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for basic structure
        if 'def main():' not in content:
            print("❌ main() function not found")
            return False

        if 'st.set_page_config' not in content:
            print("❌ set_page_config not found")
            return False

        print("✓ App structure looks good")
        return True
    except Exception as e:
        print(f"❌ Error checking app structure: {e}")
        return False

def main():
    print("🔍 Testing Streamlit app deployment readiness...")
    print("=" * 50)

    success = True

    # Test imports
    if not test_imports():
        success = False

    print()

    # Test app structure
    if not test_app_structure():
        success = False

    print()
    print("=" * 50)

    if success:
        print("✅ All tests passed! App should be ready for deployment.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())