#!/usr/bin/env python3
"""
AquaBrain Gemini REST API Test - Gemini 2.5 Pro
================================================
Tests Gemini connection using direct REST API.
No dependencies on other services.
"""

import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("[INFO] dotenv not installed, reading .env manually")
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Import requests
try:
    import requests
except ImportError:
    print("[ERROR] requests not installed. Run: pip install requests")
    sys.exit(1)


# Available models (strongest to fastest)
MODELS = {
    "pro": "gemini-2.5-pro",        # Most powerful - 25 req/day free
    "flash": "gemini-2.5-flash",    # Balanced - more requests
    "fast": "gemini-2.0-flash",     # Fastest - most requests
}

DEFAULT_MODEL = "gemini-2.5-flash"  # 500 req/day - best balance


def ask_gemini_direct(prompt: str, api_key: str, model: str = DEFAULT_MODEL) -> str:
    """Direct REST API call to Gemini."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096,
        }
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Extract text from response
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "[No text in response]")
        return "[Empty response]"

    except requests.exceptions.HTTPError as e:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", str(e))
        except:
            error_msg = str(e)
        return f"[HTTP Error] {error_msg}"
    except Exception as e:
        return f"[Error] {str(e)}"


def list_gemini_models(api_key: str) -> list:
    """List available Gemini models."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        models = []
        for model in data.get("models", []):
            name = model.get("name", "").replace("models/", "")
            if "gemini" in name.lower():
                models.append(name)
        return models
    except Exception as e:
        return [f"Error: {str(e)}"]


def test_gemini_rest():
    """Test Gemini API via REST."""
    print("=" * 60)
    print("🧠 AQUABRAIN GEMINI 2.5 FLASH TEST (500 req/day)")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ GEMINI_API_KEY not found!")
        print("   Add it to backend/.env file")
        return False

    masked_key = api_key[:10] + "..." + api_key[-4:]
    print(f"\n[1/4] API Key Found: {masked_key}")

    # Test listing models
    print("\n[2/4] Listing available models...")
    models = list_gemini_models(api_key)
    if models and not models[0].startswith("Error"):
        print(f"     Found {len(models)} Gemini models:")
        # Show 2.5 models first
        pro_models = [m for m in models if "2.5" in m or "2.0" in m]
        for model in pro_models[:6]:
            marker = "★" if model == DEFAULT_MODEL else " "
            print(f"       {marker} {model}")
    else:
        print(f"     Warning: {models[0] if models else 'No models found'}")

    # Test content generation with 2.5 Pro
    print(f"\n[3/4] Testing {DEFAULT_MODEL}...")
    response = ask_gemini_direct(
        "Say exactly: 'AquaBrain 2.5 Pro is online!'",
        api_key,
        DEFAULT_MODEL
    )

    print(f"\n     Response: {response}")

    if response.startswith("["):
        print("\n" + "=" * 60)
        print("❌ GEMINI CONNECTION FAILED")
        print("=" * 60)

        # Try fallback model
        print("\n[FALLBACK] Trying gemini-2.0-flash...")
        fallback_response = ask_gemini_direct(
            "Say exactly: 'AquaBrain fallback online!'",
            api_key,
            "gemini-2.0-flash"
        )
        print(f"     Response: {fallback_response}")

        if not fallback_response.startswith("["):
            print("\n⚠️  gemini-2.5-pro unavailable, but gemini-2.0-flash works!")
            print("   Update DEFAULT_MODEL in ai_engine.py if needed")
            return True
        return False

    print("\n" + "=" * 60)
    print("✅ GEMINI 2.5 FLASH CONNECTION SUCCESSFUL!")
    print("=" * 60)

    # Test Hebrew
    print("\n[4/4] Testing Hebrew response...")
    hebrew_response = ask_gemini_direct(
        "מה המהירות המקסימלית המותרת בצינור ספרינקלרים לפי NFPA 13? ענה בקצרה בעברית.",
        api_key,
        DEFAULT_MODEL
    )

    # Truncate long response
    if len(hebrew_response) > 300:
        hebrew_response = hebrew_response[:300] + "..."
    print(f"\n     Hebrew Response:\n     {hebrew_response}")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print(f"   Model: {DEFAULT_MODEL}")
    print("   AquaBrain AI Engine is ready! 🧠🚀")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_gemini_rest()
    sys.exit(0 if success else 1)
