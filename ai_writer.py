"""
ai_writer.py — AI suggestion engine for "Write CV with AI" feature.
Generates section-specific bullet-point suggestions via Groq or Ollama.
"""
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.1-8b-instant"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL   = "phi3"

SECTION_CONTEXT = {
    "Summary":               "a professional summary / objective statement (2–4 sentences)",
    "Skills":                "a skills list: technical tools, languages, frameworks, soft skills",
    "Experience / Projects": "work experience or projects with impact-driven bullet points",
    "Education":             "educational background with institution, degree, and dates",
    "Certifications":        "professional certifications, online courses, and achievements",
}


def _build_prompt(section_name, current_text, role, language):
    lang_note  = "Respond in Nepali." if language == "Nepali" else "Respond in English."
    role_note  = f"Target role: **{role.strip()}**." if role.strip() else "No specific target role."
    ctx        = SECTION_CONTEXT.get(section_name, "a CV section")
    existing = (
        f"Already written:\n\"\"\"\n{current_text.strip()}\n\"\"\"\nDo NOT repeat the above."
        if current_text.strip() else "Nothing written yet for this section."
    )
    return (
        f"{lang_note}\n{role_note}\n\n"
        f"You are an expert CV writer. Generate suggestions for the **{section_name}** section.\n"
        f"This section is: {ctx}.\n{existing}\n\n"
        f"Return exactly 4–5 ATS-friendly bullet points.\n"
        f"Each bullet starts with '• ', is one standalone sentence, uses strong action verbs, "
        f"includes metrics where possible, and is under 25 words.\n"
        f"Return ONLY the bullet points — no headings or extra text."
    )


def _groq_error(response):
    try:
        return response.json().get("error", {}).get("message", f"HTTP {response.status_code}")
    except Exception:
        return f"HTTP {response.status_code}"


def _call_groq(prompt, api_key):
    if not api_key or not api_key.strip():
        return "❌ **Groq API Key Missing.** Enter it in the sidebar."
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a professional CV writer specialising in ATS-optimised content."},
            {"role": "user",   "content": prompt},
        ],
        "temperature": 0.75,
        "max_tokens":  600,
    }
    try:
        r = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        return "❌ **Network Error:** Could not reach Groq. Check your connection."
    except requests.exceptions.Timeout:
        return "❌ **Timeout:** Groq took too long. Try again."
    except requests.exceptions.HTTPError:
        if r.status_code == 401:
            return "❌ **Invalid Groq API Key.** Re-enter it in the sidebar."
        return f"❌ **Groq Error:** {_groq_error(r)}"
    except Exception as exc:
        return f"❌ **Unexpected Error:** {exc}"


def _call_ollama(prompt):
    try:
        r = requests.post(OLLAMA_API_URL, json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}, timeout=120)
        r.raise_for_status()
        return r.json().get("response", "No response.").strip()
    except requests.exceptions.ConnectionError:
        return "❌ **Ollama not running.** Run `ollama serve` then `ollama pull phi3`."
    except requests.exceptions.Timeout:
        return "❌ **Timeout:** Ollama took too long."
    except Exception as exc:
        return f"❌ **Error:** {exc}"


def suggest_for_section(section_name, current_text, role="", language="English", provider="groq", groq_api_key=""):
    """
    Generate AI bullet-point suggestions for a CV section.

    Args:
        section_name:  e.g. "Summary", "Skills", "Experience / Projects"
        current_text:  What the user has already written (may be empty)
        role:          Optional target job role
        language:      "English" or "Nepali"
        provider:      "groq" or "ollama"
        groq_api_key:  Required when provider == "groq"

    Returns:
        String of bullet-point suggestions, or an error message starting with ❌
    """
    prompt = _build_prompt(section_name, current_text, role, language)
    return _call_groq(prompt, groq_api_key) if provider == "groq" else _call_ollama(prompt)
