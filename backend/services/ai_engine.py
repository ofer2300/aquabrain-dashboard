"""
AquaBrain AI Engine - Hybrid Local-First Architecture
======================================================

Multi-model support with Smart Routing:
- Ollama (Local) - RTX 4060 Ti 16GB VRAM - Zero latency
- Gemini (Cloud) - Fallback for complex reasoning
- Claude (Cloud) - Optional premium provider

Smart Router Logic:
- "python", "code", "script", "private" → Ollama (Local)
- Complex reasoning, general knowledge → Gemini (Cloud)
- Fallback: If Local fails → Cloud

Usage:
    from services.ai_engine import ask_ai, ask_aquabrain, smart_ask

    # Smart routing (auto-selects provider)
    response = smart_ask("Write a Python script to parse JSON")

    # Direct provider selection
    response = ask_ai("מה זה NFPA 13?", provider="ollama")
    response = ask_ai("Explain quantum physics", provider="gemini")

    # AquaBrain engineering mode
    response = ask_aquabrain("חשב אובדן לחץ בצינור 2 אינץ'")
"""

import os
import re
import requests
from typing import List, Dict, Optional, Literal
from dotenv import load_dotenv
from enum import Enum

load_dotenv()


# ============================================================
# Configuration
# ============================================================

class AIProvider(str, Enum):
    OLLAMA = "ollama"    # Local - RTX 4060 Ti
    GEMINI = "gemini"    # Cloud - Google
    CLAUDE = "claude"    # Cloud - Anthropic
    GPT = "gpt"          # Future


class OllamaModel(str, Enum):
    QWEN_CODER = "qwen2.5-coder:7b"      # Code generation (default)
    QWEN_14B = "qwen2.5:14b"             # General purpose
    CODELLAMA = "codellama:7b"           # Code specialist
    DEEPSEEK = "deepseek-coder:6.7b"     # Alternative coder


class ClaudeModel(str, Enum):
    HAIKU = "claude-3-5-haiku-20241022"
    SONNET = "claude-sonnet-4-20250514"
    OPUS = "claude-opus-4-20250514"


class GeminiModel(str, Enum):
    FLASH = "gemini-2.0-flash"
    FLASH_25 = "gemini-2.5-flash"
    PRO = "gemini-2.5-pro"


# Default configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LOCAL_MODEL = OllamaModel.QWEN_CODER.value

DEFAULT_PROVIDER = "ollama"  # Local-first!
DEFAULT_OLLAMA_MODEL = OllamaModel.QWEN_CODER.value
DEFAULT_GEMINI_MODEL = GeminiModel.FLASH_25.value
DEFAULT_CLAUDE_MODEL = ClaudeModel.SONNET.value

# Smart routing keywords
LOCAL_KEYWORDS = [
    "python", "code", "script", "function", "class", "def ",
    "import", "variable", "loop", "algorithm", "debug",
    "private", "confidential", "internal", "secret",
    "research", "summarize", "analyze code", "refactor",
    "write code", "create function", "implement", "generate code"
]

# Keywords that prefer cloud (strategy/reasoning)
CLOUD_KEYWORDS = [
    "why", "explain", "strategy", "compare", "recommend",
    "best practice", "architecture", "design pattern",
    "trade-off", "pros and cons", "analyze options"
]


# ============================================================
# Ollama Client (Local LLM)
# ============================================================

class OllamaClient:
    """Client for local Ollama inference on RTX 4060 Ti."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url.rstrip('/')

    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False

    def list_models(self) -> List[str]:
        """List available models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except:
            pass
        return []

    def generate(
        self,
        prompt: str,
        model: str = LOCAL_MODEL,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        num_ctx: int = 4096
    ) -> str:
        """Generate response using local LLM."""

        url = f"{self.base_url}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": num_ctx  # Context window size
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        return data.get("response", "")

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = LOCAL_MODEL,
        system_prompt: Optional[str] = None
    ) -> str:
        """Multi-turn chat with local LLM."""

        url = f"{self.base_url}/api/chat"

        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": False
        }

        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        return data.get("message", {}).get("content", "")


# ============================================================
# Gemini Client (Cloud)
# ============================================================

class GeminiClient:
    """Client for Google Gemini API."""

    MODELS = {
        "pro": "gemini-2.5-pro",
        "flash": "gemini-2.5-flash",
        "fast": "gemini-2.0-flash",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY not set!")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def generate(
        self,
        prompt: str,
        model: str = DEFAULT_GEMINI_MODEL,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """Generate content with Gemini."""

        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"[System Instructions]\n{system_prompt}\n\n[User Query]\n{prompt}"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
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
        """Multi-turn chat with Gemini."""

        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"[System]\n{system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})

        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {"contents": contents}

        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


# ============================================================
# Claude Client (Cloud)
# ============================================================

class ClaudeClient:
    """Client for Anthropic Claude API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("❌ ANTHROPIC_API_KEY not set!")
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
        """Generate content with Claude."""

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
        """Multi-turn chat with Claude."""

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version
        }

        formatted_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "assistant"
            formatted_messages.append({"role": role, "content": msg["content"]})

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
# Client Singletons
# ============================================================

_ollama_client = None
_gemini_client = None
_claude_client = None


def get_ollama_client() -> OllamaClient:
    """Get Ollama client singleton."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


def get_gemini_client() -> GeminiClient:
    """Get Gemini client singleton."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = GeminiClient()
    return _gemini_client


def get_claude_client() -> ClaudeClient:
    """Get Claude client singleton."""
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client


# ============================================================
# Smart Router
# ============================================================

def should_use_local(prompt: str) -> bool:
    """
    Determine if a prompt should be routed to local LLM.

    Routes to LOCAL (Ollama) if:
    - Contains code-related keywords
    - Mentions privacy/confidential
    - Research/analysis tasks

    Routes to CLOUD (Gemini) if:
    - Contains strategy/reasoning keywords
    - Asks "why", "explain", "compare"
    """
    prompt_lower = prompt.lower()

    # First check for CLOUD keywords (strategy/reasoning takes priority)
    for keyword in CLOUD_KEYWORDS:
        if keyword in prompt_lower:
            return False  # Use cloud for strategy/reasoning

    # Then check for LOCAL keywords
    for keyword in LOCAL_KEYWORDS:
        if keyword in prompt_lower:
            return True

    # Check for code blocks
    if "```" in prompt or "def " in prompt or "class " in prompt:
        return True

    # Default to cloud for general queries
    return False


def smart_ask(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    fallback: bool = True
) -> str:
    """
    Intelligent routing between Local and Cloud providers.

    Auto-selects provider based on prompt content:
    - Code/Python/Private → Ollama (Local)
    - General/Complex → Gemini (Cloud)

    With fallback: If local fails, automatically tries cloud.

    Args:
        prompt: The user's question/request
        system_prompt: Optional system instructions
        temperature: Creativity level (0.0-1.0)
        fallback: If True, falls back to cloud on local failure

    Returns:
        AI response string
    """
    use_local = should_use_local(prompt)

    if use_local:
        try:
            ollama = get_ollama_client()
            if ollama.is_available():
                return ollama.generate(prompt, LOCAL_MODEL, system_prompt, temperature)
            elif fallback:
                print("⚠️ Ollama not available, falling back to Gemini")
        except Exception as e:
            if fallback:
                print(f"⚠️ Local LLM failed ({e}), falling back to Gemini")
            else:
                raise

    # Use cloud (Gemini)
    gemini = get_gemini_client()
    return gemini.generate(prompt, DEFAULT_GEMINI_MODEL, system_prompt, temperature)


# ============================================================
# Unified AI Interface
# ============================================================

def ask_ai(
    prompt: str,
    provider: Literal["ollama", "gemini", "claude"] = DEFAULT_PROVIDER,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7
) -> str:
    """
    Unified AI query interface.

    Args:
        prompt: The question/request
        provider: "ollama" (local), "gemini" (cloud), or "claude" (cloud)
        model: Specific model (optional - uses default)
        system_prompt: System instructions
        temperature: Creativity (0.0-1.0)

    Examples:
        # Local (RTX 4060 Ti)
        response = ask_ai("Write Python code", provider="ollama")

        # Cloud (Gemini - default fallback)
        response = ask_ai("Explain NFPA 13", provider="gemini")

        # Cloud (Claude - premium)
        response = ask_ai("Complex analysis", provider="claude")
    """

    if provider == "ollama":
        client = get_ollama_client()
        model = model or DEFAULT_OLLAMA_MODEL
        return client.generate(prompt, model, system_prompt, temperature)

    elif provider == "gemini":
        client = get_gemini_client()
        model = model or DEFAULT_GEMINI_MODEL
        return client.generate(prompt, model, system_prompt, temperature)

    elif provider == "claude":
        client = get_claude_client()
        model = model or DEFAULT_CLAUDE_MODEL
        return client.generate(prompt, model, system_prompt, temperature)

    else:
        raise ValueError(f"Unknown provider: {provider}")


def chat_ai(
    messages: List[Dict[str, str]],
    provider: Literal["ollama", "gemini", "claude"] = DEFAULT_PROVIDER,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None
) -> str:
    """Multi-turn chat with any provider."""

    if provider == "ollama":
        client = get_ollama_client()
        model = model or DEFAULT_OLLAMA_MODEL
        return client.chat(messages, model, system_prompt)

    elif provider == "gemini":
        client = get_gemini_client()
        model = model or DEFAULT_GEMINI_MODEL
        return client.chat(messages, model, system_prompt)

    elif provider == "claude":
        client = get_claude_client()
        model = model or DEFAULT_CLAUDE_MODEL
        return client.chat(messages, model, system_prompt)

    else:
        raise ValueError(f"Unknown provider: {provider}")


# ============================================================
# AquaBrain Engineering Functions
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
    provider: Literal["ollama", "gemini", "claude"] = "gemini",  # Cloud for engineering
    model: Optional[str] = None
) -> str:
    """
    Engineering-focused AI assistant.

    Uses cloud by default for complex engineering reasoning.
    """
    return ask_ai(
        prompt=question,
        provider=provider,
        model=model,
        system_prompt=AQUABRAIN_SYSTEM_PROMPT,
        temperature=0.3  # More precise for engineering
    )


def analyze_ifc_element(
    element_data: Dict,
    analysis_type: str = "compliance",
    provider: Literal["ollama", "gemini", "claude"] = "gemini"
) -> str:
    """Analyze IFC/BIM element for compliance."""
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
# Legacy Compatibility
# ============================================================

def ask_gemini(prompt: str, model: str = DEFAULT_GEMINI_MODEL, temperature: float = 0.7) -> str:
    """Legacy: Use ask_ai with gemini provider."""
    return ask_ai(prompt, provider="gemini", model=model, temperature=temperature)


def ask_claude(prompt: str, model: str = DEFAULT_CLAUDE_MODEL, temperature: float = 0.7) -> str:
    """Legacy: Use ask_ai with claude provider."""
    return ask_ai(prompt, provider="claude", model=model, temperature=temperature)


def chat_with_gemini(messages: List[Dict[str, str]], model: str = DEFAULT_GEMINI_MODEL) -> str:
    """Legacy: Use chat_ai with gemini provider."""
    return chat_ai(messages, provider="gemini", model=model)


def get_client() -> GeminiClient:
    """Legacy: Get default client (Gemini)."""
    return get_gemini_client()


# ============================================================
# Exports
# ============================================================

__all__ = [
    # Providers & Models
    'AIProvider',
    'OllamaModel',
    'ClaudeModel',
    'GeminiModel',
    # Clients
    'OllamaClient',
    'ClaudeClient',
    'GeminiClient',
    'get_ollama_client',
    'get_gemini_client',
    'get_claude_client',
    # Smart Router
    'smart_ask',
    'should_use_local',
    # Unified Interface
    'ask_ai',
    'chat_ai',
    # AquaBrain
    'ask_aquabrain',
    'analyze_ifc_element',
    'AQUABRAIN_SYSTEM_PROMPT',
    # Constants
    'OLLAMA_BASE_URL',
    'LOCAL_MODEL',
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
    """Test AI provider connections."""

    print("=" * 60)
    print("🧠 AquaBrain AI Engine - Hybrid Local-First Architecture")
    print("=" * 60)

    results = {}

    # Test Ollama (Local)
    if provider in ["all", "ollama"]:
        print("\n[Ollama] Testing local LLM (RTX 4060 Ti)...")
        try:
            ollama = get_ollama_client()
            if ollama.is_available():
                models = ollama.list_models()
                print(f"    ✅ Ollama connected! Models: {models[:3]}...")
                response = ollama.generate("Say 'Local OK' in 2 words.", LOCAL_MODEL)
                print(f"    📝 Response: {response.strip()[:50]}")
                results["ollama"] = True
            else:
                print("    ⚠️ Ollama server not running")
                results["ollama"] = False
        except Exception as e:
            print(f"    ❌ Ollama: {e}")
            results["ollama"] = False

    # Test Gemini (Cloud)
    if provider in ["all", "gemini"]:
        print("\n[Gemini] Testing cloud connection...")
        try:
            response = ask_ai("Say 'Cloud OK' in 2 words.", provider="gemini")
            print(f"    ✅ Gemini: {response.strip()[:50]}")
            results["gemini"] = True
        except Exception as e:
            print(f"    ❌ Gemini: {e}")
            results["gemini"] = False

    # Test Claude (Optional)
    if provider in ["all", "claude"]:
        print("\n[Claude] Testing cloud connection...")
        try:
            response = ask_ai("Say 'Claude OK' in 2 words.", provider="claude")
            print(f"    ✅ Claude: {response.strip()[:50]}")
            results["claude"] = True
        except Exception as e:
            if "ANTHROPIC_API_KEY" in str(e):
                print("    ⚠️ Claude: API key not configured (optional)")
            else:
                print(f"    ❌ Claude: {e}")
            results["claude"] = False

    # Test Smart Router
    if results.get("ollama") or results.get("gemini"):
        print("\n[Smart Router] Testing auto-routing...")
        try:
            response = smart_ask("Write a simple Python hello world function")
            print(f"    ✅ Smart Router: {response.strip()[:80]}...")
        except Exception as e:
            print(f"    ❌ Smart Router: {e}")

    print("\n" + "=" * 60)
    working = [k for k, v in results.items() if v]
    print(f"✅ Active providers: {', '.join(working) if working else 'None'}")
    print(f"🏠 Local-first: {'Ollama' if results.get('ollama') else 'Gemini (fallback)'}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    test_connection()
