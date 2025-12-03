#!/usr/bin/env python3
"""
AquaBrain Gemini API Key Verification Script
=============================================
Tests if the GEMINI_API_KEY is valid and accessible.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_gemini_api():
    """Test Gemini API key validity."""
    print("=" * 60)
    print("AQUABRAIN GEMINI API KEY VERIFICATION")
    print("=" * 60)

    # Step 1: Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("[1/4] Environment loaded from .env")
    except ImportError:
        print("[1/4] python-dotenv not installed, using system env only")

    # Step 2: Check if API key exists
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("\n[2/4] API Key Status: NOT FOUND")
        print("\n" + "=" * 60)
        print("RESULT: KEY MISSING")
        print("=" * 60)
        print("\nTo fix this, add GEMINI_API_KEY to your .env file:")
        print("  echo 'GEMINI_API_KEY=your_api_key_here' >> .env")
        print("\nGet your API key from: https://makersuite.google.com/app/apikey")
        return False

    # Mask API key for display
    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    print(f"[2/4] API Key Found: {masked_key}")

    # Step 3: Import and configure Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        print("[3/4] Gemini SDK configured successfully")
    except Exception as e:
        print(f"\n[3/4] Failed to configure Gemini SDK: {e}")
        print("\n" + "=" * 60)
        print("RESULT: SDK CONFIGURATION FAILED")
        print("=" * 60)
        return False

    # Step 4: Test API call
    print("[4/4] Testing API connection...")

    try:
        # Try to list available models first (lighter API call)
        models = list(genai.list_models())
        gemini_models = [m.name for m in models if 'gemini' in m.name.lower()]

        print(f"\n     Available Gemini models: {len(gemini_models)}")
        for model in gemini_models[:5]:  # Show first 5
            print(f"       - {model}")

        # Now try a simple generation
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content("Say 'AquaBrain is online!' in one short sentence.")

        print(f"\n     Test Response: {response.text.strip()}")

        print("\n" + "=" * 60)
        print("GEMINI API KEY IS VALID")
        print("=" * 60)
        print("\nThe Gemini brain is ready to power AquaBrain AI features!")
        return True

    except Exception as e:
        error_msg = str(e)
        print(f"\n     API Error: {error_msg}")

        print("\n" + "=" * 60)
        print("API KEY INVALID OR EXPIRED")
        print("=" * 60)

        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            print("\nThe API key appears to be invalid.")
            print("Please generate a new key at: https://makersuite.google.com/app/apikey")
        elif "quota" in error_msg.lower():
            print("\nAPI quota exceeded. Wait or upgrade your plan.")
        elif "permission" in error_msg.lower():
            print("\nAPI key lacks required permissions.")
        else:
            print(f"\nUnexpected error: {error_msg}")

        return False


if __name__ == "__main__":
    success = test_gemini_api()
    sys.exit(0 if success else 1)
