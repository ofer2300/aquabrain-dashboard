"""
AquaBrain AI Engine - Multi-Model Support
==========================================

מנוע AI עם תמיכה ב:
- Claude (Anthropic) - Haiku, Sonnet, Opus
- Gemini (Google) - Flash, Pro

שימוש:
    from services.ai_engine import ask_ai, ask_aquabrain

    # שאלה עם Claude (ברירת מחדל)
    response = ask_ai("מה זה NFPA 13?")

    # שאלה עם Gemini
    response = ask_ai("מה זה NFPA 13?", provider="gemini")

    # שאלה הנדסית עם AquaBrain
    response = ask_aquabrain("חשב אובדן לחץ בצינור 2 אינץ'")
"""

import os
import requests
from typing import List, Dict, Optional, Literal
from dotenv import load_dotenv
from enum import Enum

load_dotenv()


# ============================================================
# Configuration
# ============================================================

class AIProvider(str, Enum):
    CLAUDE = "claude"
    GEMINI = "gemini"
    GPT = "gpt"  # לעתיד


class ClaudeModel(str, Enum):
    HAIKU = "claude-3-5-haiku-20241022"      # מהיר וזול
    SONNET = "claude-sonnet-4-20250514"       # מאוזן - מומלץ!
    OPUS = "claude-opus-4-20250514"           # הכי חזק


class GeminiModel(str, Enum):
    FLASH = "gemini-2.0-flash"       # מהיר - 1500/day
    FLASH_25 = "gemini-2.5-flash"    # מאוזן - 500/day
    PRO = "gemini-2.5-pro"           # חזק - 25/day


# Default models
DEFAULT_PROVIDER = "gemini"  # Gemini as default (free tier)
DEFAULT_CLAUDE_MODEL = ClaudeModel.SONNET.value
DEFAULT_GEMINI_MODEL = GeminiModel.FLASH_25.value  # 500 req/day


# ============================================================
# Claude Client
# ============================================================

class ClaudeClient:
    """קליינט ל-Anthropic Claude API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("❌ ANTHROPIC_API_KEY לא הוגדר!")
        self.base_url = "https://api.anthropic.com/v1"
        self.api_version = "2023-06-01"

    def generate(
        self,
        prompt: str,
        model: str = DEFAULT_CLAUDE_MODEL,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """יצירת תוכן עם Claude."""

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version
        }

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }

        if system_prompt:
            payload["system"] = system_prompt

        if temperature != 1.0:
            payload["temperature"] = temperature

        response = requests.post(
            f"{self.base_url}/messages",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()

        data = response.json()
        return data["content"][0]["text"]

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_CLAUDE_MODEL,
        system_prompt: Optional[str] = None
    ) -> str:
        """צ'אט רב-תורות עם Claude."""

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version
        }

        # המרת פורמט הודעות
        formatted_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "assistant"
            formatted_messages.append({
                "role": role,
                "content": msg["content"]
            })

        payload = {
            "model": model,
            "max_tokens": 4096,
            "messages": formatted_messages
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            f"{self.base_url}/messages",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()

        data = response.json()
        return data["content"][0]["text"]


# ============================================================
# Gemini Client
# ============================================================

class GeminiClient:
    """קליינט ל-Google Gemini API."""

    # מודלים זמינים (Free Tier)
    MODELS = {
        "pro": "gemini-2.5-pro",        # הכי חזק - 25 בקשות/יום
        "flash": "gemini-2.5-flash",    # מאוזן - 500 בקשות/יום (ברירת מחדל)
        "fast": "gemini-2.0-flash",     # הכי מהיר - 1500 בקשות/יום
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY לא הוגדר!")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def generate(
        self,
        prompt: str,
        model: str = DEFAULT_GEMINI_MODEL,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """יצירת תוכן עם Gemini."""

        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"

        # בניית הפרומפט עם system instructions
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"[System Instructions]\n{system_prompt}\n\n[User Query]\n{prompt}"

        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = DEFAULT_GEMINI_MODEL,
        system_prompt: Optional[str] = None
    ) -> str:
        """צ'אט רב-תורות עם Gemini."""

        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"

        contents = []

        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"[System Instructions]\n{system_prompt}"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "מובן. אפעל לפי ההוראות."}]
            })

        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        payload = {"contents": contents}

        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


# ============================================================
# Unified AI Interface
# ============================================================

_claude_client = None
_gemini_client = None


def get_claude_client() -> ClaudeClient:
    """מחזיר instance יחיד של Claude client."""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client


def get_gemini_client() -> GeminiClient:
    """מחזיר instance יחיד של Gemini client."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client


def ask_ai(
    prompt: str,
    provider: Literal["claude", "gemini"] = DEFAULT_PROVIDER,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7
) -> str:
    """
    שאלה אחודה לכל ה-AI providers.

    Args:
        prompt: השאלה
        provider: "claude" או "gemini" (ברירת מחדל: gemini)
        model: שם המודל (אופציונלי - ייקח ברירת מחדל)
        system_prompt: הוראות מערכת
        temperature: רמת יצירתיות (0.0-1.0)

    דוגמאות:
        # Gemini (ברירת מחדל - 500 req/day free)
        response = ask_ai("מה זה NFPA 13?")

        # Claude
        response = ask_ai("מה זה NFPA 13?", provider="claude")

        # מודל ספציפי
        response = ask_ai("...", provider="gemini", model="gemini-2.5-pro")
    """

    if provider == "claude":
        client = get_claude_client()
        model = model or DEFAULT_CLAUDE_MODEL
        return client.generate(prompt, model, system_prompt, temperature)

    elif provider == "gemini":
        client = get_gemini_client()
        model = model or DEFAULT_GEMINI_MODEL
        return client.generate(prompt, model, system_prompt, temperature)

    else:
        raise ValueError(f"Provider לא נתמך: {provider}")


def chat_ai(
    messages: List[Dict[str, str]],
    provider: Literal["claude", "gemini"] = DEFAULT_PROVIDER,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None
) -> str:
    """צ'אט רב-תורות אחוד."""

    if provider == "claude":
        client = get_claude_client()
        model = model or DEFAULT_CLAUDE_MODEL
        return client.chat(messages, model, system_prompt)

    elif provider == "gemini":
        client = get_gemini_client()
        model = model or DEFAULT_GEMINI_MODEL
        return client.chat(messages, model, system_prompt)

    else:
        raise ValueError(f"Provider לא נתמך: {provider}")


# ============================================================
# AquaBrain Specialized Functions
# ============================================================

AQUABRAIN_SYSTEM_PROMPT = """אתה AquaBrain - מומחה להנדסת מערכות כיבוי אש וספרינקלרים.

התמחויות:
- תקן NFPA 13 (אמריקאי) - כל הגרסאות
- תקן ישראלי ת"י 1596
- חישובי הידראוליקה (Hazen-Williams, Darcy-Weisbach)
- תכנון מערכות ספרינקלרים (Wet, Dry, Deluge, Pre-action)
- ניתוח קבצי IFC/BIM
- סיווגי סיכון (Light Hazard, Ordinary Hazard Group 1/2, Extra Hazard Group 1/2)
- חישובי צפיפות ושטח פעולה (Design Area)
- בחירת ראשי ספרינקלרים (K-factor, RTI, Temperature Rating)

הנחיות:
1. ענה בעברית מקצועית וברורה
2. הסבר חישובים שלב אחר שלב
3. ציין תמיד את התקן הרלוונטי ומספר הסעיף
4. אם חסר מידע קריטי - שאל שאלות הבהרה
5. הצג נוסחאות ויחידות מידה
6. התייחס לגורמי בטיחות ומרווחים"""


def ask_aquabrain(
    question: str,
    provider: Literal["claude", "gemini"] = DEFAULT_PROVIDER,
    model: Optional[str] = None
) -> str:
    """
    שאלה הנדסית ל-AquaBrain.

    דוגמאות:
        response = ask_aquabrain("חשב אובדן לחץ בצינור 2 אינץ' באורך 30 מטר")
        response = ask_aquabrain("מה הדרישות לספרינקלרים בחניון תת-קרקעי?")
        response = ask_aquabrain("...", provider="claude")  # עם Claude
    """
    return ask_ai(
        prompt=question,
        provider=provider,
        model=model,
        system_prompt=AQUABRAIN_SYSTEM_PROMPT,
        temperature=0.3  # יותר דייקני למשימות הנדסיות
    )


def analyze_ifc_element(
    element_data: Dict,
    analysis_type: str = "compliance",
    provider: Literal["claude", "gemini"] = DEFAULT_PROVIDER
) -> str:
    """
    ניתוח אלמנט IFC.

    Args:
        element_data: נתוני האלמנט מקובץ IFC
        analysis_type: סוג הניתוח (compliance, hydraulic, spacing)
        provider: ה-AI provider
    """
    import json

    prompt = f"""נתח את אלמנט ה-IFC הבא:

```json
{json.dumps(element_data, indent=2, ensure_ascii=False)}
```

סוג ניתוח: {analysis_type}

בצע:
1. זהה את סוג האלמנט
2. בדוק תאימות לתקן הרלוונטי
3. הצג ממצאים ובעיות פוטנציאליות
4. הצע תיקונים אם נדרש"""

    return ask_aquabrain(prompt, provider=provider)


# ============================================================
# Legacy Functions (תאימות לאחור)
# ============================================================

def ask_gemini(
    prompt: str,
    model: str = DEFAULT_GEMINI_MODEL,
    temperature: float = 0.7
) -> str:
    """תאימות לאחור - משתמש ב-ask_ai עם Gemini."""
    return ask_ai(prompt, provider="gemini", model=model, temperature=temperature)


def ask_claude(
    prompt: str,
    model: str = DEFAULT_CLAUDE_MODEL,
    temperature: float = 0.7
) -> str:
    """תאימות לאחור - משתמש ב-ask_ai עם Claude."""
    return ask_ai(prompt, provider="claude", model=model, temperature=temperature)


def chat_with_gemini(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_GEMINI_MODEL
) -> str:
    """תאימות לאחור - צ'אט עם Gemini."""
    return chat_ai(messages, provider="gemini", model=model)


def get_client() -> GeminiClient:
    """תאימות לאחור - מחזיר Gemini client."""
    return get_gemini_client()


# ============================================================
# Exports
# ============================================================

__all__ = [
    # Providers & Models
    'AIProvider',
    'ClaudeModel',
    'GeminiModel',
    # Clients
    'ClaudeClient',
    'GeminiClient',
    'get_claude_client',
    'get_gemini_client',
    # Unified Interface
    'ask_ai',
    'chat_ai',
    # AquaBrain
    'ask_aquabrain',
    'analyze_ifc_element',
    'AQUABRAIN_SYSTEM_PROMPT',
    # Legacy
    'ask_gemini',
    'ask_claude',
    'chat_with_gemini',
    'get_client',
]


# ============================================================
# Testing
# ============================================================

def test_connection(provider: str = "all"):
    """בדיקת חיבור ל-AI providers."""

    print("=" * 60)
    print("🧠 AquaBrain - בדיקת חיבור AI (Multi-Model)")
    print("=" * 60)

    results = {}

    # Test Gemini (default, free tier)
    if provider in ["all", "gemini"]:
        print("\n[Gemini] בודק חיבור...")
        try:
            response = ask_ai(
                "Say 'Gemini connected!' in exactly 2 words.",
                provider="gemini"
            )
            print(f"    ✅ Gemini: {response.strip()}")
            results["gemini"] = True
        except Exception as e:
            print(f"    ❌ Gemini: {e}")
            results["gemini"] = False

    # Test Claude (requires API key)
    if provider in ["all", "claude"]:
        print("\n[Claude] בודק חיבור...")
        try:
            response = ask_ai(
                "Say 'Claude connected!' in exactly 2 words.",
                provider="claude"
            )
            print(f"    ✅ Claude: {response.strip()}")
            results["claude"] = True
        except Exception as e:
            error_msg = str(e)
            if "ANTHROPIC_API_KEY" in error_msg:
                print(f"    ⚠️  Claude: API key not configured (optional)")
            else:
                print(f"    ❌ Claude: {e}")
            results["claude"] = False

    # Test AquaBrain with working provider
    if any(results.values()):
        print("\n[AquaBrain] בודק מומחיות...")
        working_provider = "gemini" if results.get("gemini") else "claude"
        try:
            response = ask_aquabrain(
                "מה הקוטר המינימלי לצינור ענף ספרינקלרים לפי NFPA 13?",
                provider=working_provider
            )
            print(f"    ✅ AquaBrain ({working_provider}):")
            print(f"       {response.strip()[:150]}...")
        except Exception as e:
            print(f"    ❌ AquaBrain: {e}")

    print("\n" + "=" * 60)

    # Summary
    working = [k for k, v in results.items() if v]
    if working:
        print(f"✅ מחובר: {', '.join(working)}")
        print(f"   ברירת מחדל: {DEFAULT_PROVIDER} ({DEFAULT_GEMINI_MODEL})")
    else:
        print("❌ אין חיבור לאף provider")

    print("=" * 60)
    return results


if __name__ == "__main__":
    test_connection()
