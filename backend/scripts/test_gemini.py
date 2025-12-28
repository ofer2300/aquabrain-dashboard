import os
import google.generativeai as genai
from dotenv import load_dotenv

# טעינת קובץ הסודות
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

api_key = os.getenv("GEMINI_API_KEY")

print("=======================================")
print(" AQUABRAIN GEMINI CONNECTION TEST")
print("=======================================")

if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found in .env")
    exit(1)

print(f"🔑 Key found: {api_key[:5]}...{api_key[-4:]}")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    print("📡 Sending test signal to Google AI...")
    response = model.generate_content("Hello AquaBrain, are you online?")
    print("\n✅ SUCCESS! Response from Gemini:")
    print(f"   '{response.text}'")
    print("\n🧠 The Brain is Connected.")
except Exception as e:
    print(f"\n❌ CONNECTION FAILED: {str(e)}")
