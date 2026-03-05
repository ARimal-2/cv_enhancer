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
    "Personal Info":         "personal identity and contact details",
    "Summary":               "a professional summary / objective statement (2–4 sentences)",
    "Skills":                "a skills list: technical tools, languages, frameworks, and grouped skills",
    "Experience / Projects": "work experience or projects with CAR-style (Challenge, Action, Result) impact-driven bullet points",
    "Education":             "educational background formatted professionally with institution and degree",
    "Certifications":        "professional certifications and online courses formatted professionally",
    "Languages":             "language proficiency levels (e.g., 'English – Professional, Nepali – Native')",
}


def _build_prompt(section_name, current_text, role, language):
    lang_note  = "Respond in Nepali." if language == "Nepali" else "Respond in English."
    role_note  = f"Target role: **{role.strip()}**." if role.strip() else "No specific target role."
    ctx        = SECTION_CONTEXT.get(section_name, "a CV section")
    existing   = (
        f"Input text to enhance:\n\"\"\"\n{current_text.strip()}\n\"\"\"\n"
        if current_text.strip() else "Nothing written yet for this section."
    )
    
    base_instructions = f"{lang_note}\n{role_note}\n\n"
    base_instructions += f"You are an expert CV writer. Your task is to ENHANCE the user's input for the **{section_name}** section.\n"
    base_instructions += f"This section is: {ctx}.\n{existing}\n\n"

    if section_name == "Summary":
        prompt = (
            f"{base_instructions}"
            f"Please rewrite the summary into 2-4 compelling sentences that highlight value. "
            f"Use a professional tone and ensure it is ATS-friendly. "
            f"Return ONLY the enhanced summary text."
        )
    elif section_name == "Experience / Projects":
        prompt = (
            f"{base_instructions}"
            f"Convert the input into CAR-style (Challenge, Action, Result) bullet points. "
            f"Each bullet should start with '• ', use strong action verbs, and include metrics where possible. "
            f"Return exactly 3-5 high-impact bullet points. "
            f"Return ONLY the bullet points."
        )
    elif section_name == "Skills":
        prompt = (
            f"{base_instructions}"
            f"Organize these skills into logical groups (e.g. Languages, Frameworks, Tools). "
            f"Polish the names and ensure they are professional. "
            f"Return the polished skills, preferably as a clean list or grouped text."
        )
    elif section_name == "Education":
        prompt = (
            f"{base_instructions}"
            f"Create a polished, professional education entry based on the input. "
            f"Ensure common degree names and institution names are formatted correctly. "
            f"Return ONLY the polished entry."
        )
    elif section_name == "Certifications":
        prompt = (
            f"{base_instructions}"
            f"Format these certifications professionally. "
            f"Return ONLY the polished names."
        )
    elif section_name == "Languages":
        prompt = (
            f"{base_instructions}"
            f"Format the languages with proficiency levels (e.g., 'English – Professional, Nepali – Native'). "
            f"Return ONLY the formatted list."
        )
    else:
        prompt = (
            f"{base_instructions}"
            f"Return exactly 4–5 ATS-friendly bullet points.\n"
            f"Each bullet starts with '• ', is one standalone sentence, uses strong action verbs, "
            f"includes metrics where possible, and is under 25 words.\n"
            f"Return ONLY the bullet points — no headings or extra text."
        )
    
    return prompt


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
