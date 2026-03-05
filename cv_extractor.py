"""
cv_extractor.py
AI-powered structured data extractor for CV/resume text.
Returns a validated Python dict matching the standardized CV schema.
"""
import re
import json
import requests

GROQ_API_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL    = "llama-3.1-8b-instant"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL  = "phi3"

# ── JSON schema shown to the AI ──────────────────────────────────────────────
_SCHEMA = """{
  "first_name": "string (mandatory)",
  "last_name": "string (mandatory)",
  "email": "string or null",
  "phone_number": "string with country code if available, or null",
  "linkedin": "full URL string or null",
  "github": "full URL string or null",
  "profile_image": "URL string or brief description or null",
  "professional_summary": "string (mandatory)",
  "technical_skills": ["array of skill strings (mandatory)"],
  "professional_experience": [
    {
      "job_title": "string (mandatory)",
      "company": "string (mandatory)",
      "location": "string (mandatory)",
      "start_date": "YYYY-MM (mandatory)",
      "end_date": "YYYY-MM or Present (mandatory)",
      "achievements": ["array of achievement strings with metrics (mandatory)"]
    }
  ],
  "projects": [
    {
      "project_name": "string (mandatory)",
      "description": "string (mandatory)",
      "technologies_used": ["array of strings"] or null,
      "impact_metrics": "string or null"
    }
  ],
  "education": [
    {
      "degree": "string (mandatory)",
      "university": "string (mandatory)",
      "location": "string or null",
      "start_year": "YYYY or null",
      "end_year": "YYYY or null"
    }
  ],
  "certifications": ["array of strings"] or null,
  "languages": ["array of spoken/written languages"] or null
}"""


def _build_prompt(resume_text: str) -> str:
    return f"""You are a precise, structured CV parser. Your only job is to extract data.

Extract all information from the CV below and return it as a single, valid JSON object.

Use this exact schema:
{_SCHEMA}

Rules (follow strictly):
1. Return ONLY the raw JSON object — no markdown, no code fences, no explanations.
2. Mandatory fields: make your best inference if not explicit; never omit them.
3. Optional fields: use JSON null (not the string "null") if information is absent.
4. Normalize all dates to YYYY-MM format. If only a year is present, use YYYY-01.
5. For achievements, preserve metrics and quantified results exactly.
6. Do NOT invent data that is not present in the CV.

CV TEXT:
---
{resume_text}
---

JSON:"""


def _extract_json(text: str):
    """Return parsed dict from AI response, tolerating surrounding text."""
    text = text.strip()
    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Extract first {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _groq_error(r) -> str:
    try:
        return r.json().get("error", {}).get("message", f"HTTP {r.status_code}")
    except Exception:
        return f"HTTP {r.status_code}"


# ── Groq ─────────────────────────────────────────────────────────────────────
def _call_groq(prompt: str, api_key: str):
    if not api_key or not api_key.strip():
        return None, "❌ **Groq API Key Missing.** Enter it in the sidebar."

    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a CV parser that returns ONLY valid JSON. "
                    "Never add explanations, markdown code fences, or any text outside the JSON object."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.05,   # very low — we want deterministic structured output
        "max_tokens": 2500,
    }
    try:
        r = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=90)
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip()
        data = _extract_json(raw)
        if data is None:
            return None, f"❌ **JSON Parse Error:** AI returned malformed JSON.\n\nRaw response:\n```\n{raw[:400]}\n```"
        return data, None
    except requests.exceptions.ConnectionError:
        return None, "❌ **Network Error:** Could not reach Groq."
    except requests.exceptions.Timeout:
        return None, "❌ **Timeout:** Groq took too long. Try again."
    except requests.exceptions.HTTPError:
        if r.status_code == 401:
            return None, "❌ **Invalid Groq API Key.** Re-enter it in the sidebar."
        return None, f"❌ **Groq Error:** {_groq_error(r)}"
    except Exception as exc:
        return None, f"❌ **Unexpected Error:** {exc}"


# ── Ollama ────────────────────────────────────────────────────────────────────
def _call_ollama(prompt: str):
    try:
        r = requests.post(
            OLLAMA_API_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        raw = r.json().get("response", "").strip()
        data = _extract_json(raw)
        if data is None:
            return None, "❌ **JSON Parse Error:** Ollama returned malformed JSON. Try Groq instead."
        return data, None
    except requests.exceptions.ConnectionError:
        return None, "❌ **Ollama not running.** Run `ollama serve` then `ollama pull phi3`."
    except requests.exceptions.Timeout:
        return None, "❌ **Timeout:** Ollama took too long."
    except Exception as exc:
        return None, f"❌ **Error:** {exc}"


# ── Public interface ──────────────────────────────────────────────────────────
def extract_cv_data(resume_text: str, provider: str = "groq", groq_api_key: str = ""):
    """
    Extract structured CV data from plain resume text using AI.

    Args:
        resume_text:   Plain text content of the CV.
        provider:      "groq" (cloud) or "ollama" (local).
        groq_api_key:  Required when provider == "groq".

    Returns:
        (dict, None)        on success — dict matches the standardized CV schema.
        (None, error_str)   on failure — error_str starts with ❌.
    """
    prompt = _build_prompt(resume_text)
    if provider == "groq":
        return _call_groq(prompt, groq_api_key)
    return _call_ollama(prompt)
