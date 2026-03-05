"""
ai_engine.py
------------
Interfaces with either:
  - Local Ollama API  (http://localhost:11434)  — for local development
  - Groq Cloud API    (https://api.groq.com)    — for deployment / when Ollama is unavailable

Model used: phi3 (via Ollama) or llama3-8b-8192 (via Groq)
"""
import os
import requests

# ── Ollama settings ─────────────────────────────────────────────────────────
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3"

# ── Groq settings ───────────────────────────────────────────────────────────
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"   # free tier model; supports the same prompts


# ─────────────────────────────────────────────────────────────────────────────
# Shared prompt builder
# ─────────────────────────────────────────────────────────────────────────────
def _build_prompt(resume_text: str) -> str:
    return f"""You are an expert career coach and professional resume writer with 15+ years of experience.

Carefully analyze the resume below and provide specific, actionable suggestions to make it significantly stronger.

Your response MUST cover all four areas:

1. **Bullet Point Improvements** – Rewrite weak bullet points using the CAR method (Context, Action, Result). Quantify outcomes where possible.
2. **Professional Tone & Language** – Identify any informal phrasing and suggest polished alternatives.
3. **Stronger Action Verbs** – List the weak or repeated verbs used and provide powerful alternatives (e.g., "did" → "orchestrated").
4. **Missing Skills & Sections** – Point out any critical sections (summary, certifications, metrics, links) or skills that are absent.

Format your response in clear Markdown with headers for each section.

---
RESUME:
{resume_text}
---

Provide your detailed analysis below:"""


# ─────────────────────────────────────────────────────────────────────────────
# Ollama (local)
# ─────────────────────────────────────────────────────────────────────────────
def _call_ollama(resume_text: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": _build_prompt(resume_text),
        "stream": False,
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "No response received from the model.")
    except requests.exceptions.ConnectionError:
        return (
            "❌ **Connection Error:** Could not reach the Ollama API at `localhost:11434`.\n\n"
            "Please make sure:\n"
            "- Ollama is installed and running (`ollama serve`)\n"
            "- The `phi3` model is pulled (`ollama pull phi3`)\n\n"
            "Or switch to **Groq** in the sidebar — no local install needed."
        )
    except requests.exceptions.Timeout:
        return "❌ **Timeout:** Ollama took too long to respond. Try again or switch to Groq."
    except requests.exceptions.RequestException as exc:
        return f"❌ **Ollama API Error:** {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Groq (cloud — free tier)
# ─────────────────────────────────────────────────────────────────────────────
def _call_groq(resume_text: str, api_key: str) -> str:
    if not api_key or not api_key.strip():
        return (
            "❌ **Groq API Key Missing.**\n\n"
            "Get a free key at [console.groq.com](https://console.groq.com) and paste it in the sidebar."
        )

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert career coach and professional resume writer."},
            {"role": "user", "content": _build_prompt(resume_text)},
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "❌ **Network Error:** Could not reach the Groq API. Check your internet connection."
    except requests.exceptions.Timeout:
        return "❌ **Timeout:** Groq API took too long. Please try again."
    except requests.exceptions.HTTPError as exc:
        if response.status_code == 401:
            return "❌ **Invalid Groq API Key.** Please check and re-enter your key in the sidebar."
        return f"❌ **Groq API Error ({response.status_code}):** {exc}"
    except Exception as exc:
        return f"❌ **Unexpected Error:** {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────
def improve_resume(resume_text: str, provider: str = "ollama", groq_api_key: str = "") -> str:
    """
    Generate AI resume improvement suggestions.

    Args:
        resume_text:  Plain text of the resume.
        provider:     "ollama" (local) or "groq" (cloud).
        groq_api_key: Required when provider is "groq".

    Returns:
        Markdown-formatted improvement suggestions.
    """
    if provider == "groq":
        return _call_groq(resume_text, groq_api_key)
    else:
        return _call_ollama(resume_text)
