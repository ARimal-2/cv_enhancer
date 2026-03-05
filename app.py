"""
app.py
------
AI Resume Improver — Main Streamlit Application.

Run locally:
    streamlit run app.py

Deploy to Streamlit Cloud:
    Push to GitHub → connect repo at share.streamlit.io
    Set GROQ_API_KEY in Streamlit Cloud secrets (optional default).
"""

import os
import streamlit as st

from parser import extract_text
from ai_engine import improve_resume
from ats_matcher import calculate_similarity

# ─────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Resume Improver",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        min-height: 100vh;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(15, 12, 41, 0.85) !important;
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    .hero-title {
        text-align: center;
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #a78bfa, #38bdf8, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.2rem;
    }
    .hero-subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 1rem;
        margin-bottom: 2rem;
    }

    .glass-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 16px;
        padding: 1.4rem 1.75rem;
        backdrop-filter: blur(10px);
        margin-bottom: 1rem;
    }
    .section-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #a78bfa;
        margin-bottom: 0.5rem;
    }
    .score-badge {
        display: inline-block;
        font-size: 3.2rem;
        font-weight: 700;
        line-height: 1;
    }
    .score-label { font-size: 0.9rem; color: #94a3b8; margin-top: 0.25rem; }
    .chip {
        display: inline-block;
        background: rgba(167,139,250,0.15);
        border: 1px solid rgba(167,139,250,0.4);
        color: #c4b5fd;
        border-radius: 999px;
        padding: 0.25rem 0.75rem;
        font-size: 0.78rem;
        font-weight: 500;
        margin: 0.2rem;
    }
    hr { border-color: rgba(255,255,255,0.08); }

    .stTextArea textarea {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.15) !important;
        color: #e2e8f0 !important;
        border-radius: 10px !important;
    }
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #7c3aed, #2563eb) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.03em !important;
        transition: opacity 0.2s ease !important;
    }
    .stButton > button:hover { opacity: 0.88 !important; }

    .provider-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar — AI Provider Settings
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ AI Provider")
    st.markdown("---")

    provider = st.radio(
        "Choose backend:",
        options=["groq", "ollama"],
        format_func=lambda x: "☁️ Groq (Cloud — free)" if x == "groq" else "🖥️ Ollama (Local — phi3)",
        index=0,
        key="provider_select",
        help="Groq works without any local setup. Ollama requires Ollama installed locally.",
    )

    groq_api_key = ""
    if provider == "groq":
        st.markdown("#### 🔑 Groq API Key")
        # Allow key via env var (for Streamlit Cloud secrets) or manual input
        env_key = os.environ.get("GROQ_API_KEY", "")
        groq_api_key = st.text_input(
            "Groq API Key",
            value=env_key,
            type="password",
            placeholder="gsk_...",
            label_visibility="collapsed",
            key="groq_key",
        )
        st.markdown(
            "Get a **free** key at [console.groq.com](https://console.groq.com) — "
            "no credit card needed.",
            unsafe_allow_html=True,
        )
    else:
        st.info(
            "Make sure Ollama is running:\n\n"
            "```\nollama serve\nollama pull phi3\n```",
        )

    st.markdown("---")
    st.markdown("### 📘 About")
    st.markdown(
        "**AI Resume Improver** uses AI to review your resume against a job description "
        "and generate targeted improvements.\n\n"
        "- 📄 **Parser** — pdfplumber\n"
        "- 🤖 **AI** — Groq or Ollama\n"
        "- 📊 **ATS** — scikit-learn TF-IDF"
    )

# ─────────────────────────────────────────────
# Hero Header
# ─────────────────────────────────────────────
st.markdown('<h1 class="hero-title">📄 AI Resume Improver</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-subtitle">Upload your resume · Paste a job description · Get AI-powered improvements & ATS score</p>',
    unsafe_allow_html=True,
)

# Provider badge
badge_color = "#38bdf8" if provider == "groq" else "#a78bfa"
badge_label = "☁️ Groq Cloud" if provider == "groq" else "🖥️ Ollama · phi3"
st.markdown(
    f'<div style="text-align:center; margin-bottom:1.5rem;">'
    f'<span class="provider-badge" style="background:rgba(56,189,248,0.15); '
    f'border:1px solid {badge_color}; color:{badge_color};">{badge_label}</span></div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# Input Section
# ─────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown('<div class="section-label">📎 Upload Resume (PDF)</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Resume PDF",
        type=["pdf"],
        label_visibility="collapsed",
        key="resume_uploader",
    )
    if uploaded_file:
        st.success(f"✅ Loaded: **{uploaded_file.name}**")

with col_right:
    st.markdown('<div class="section-label">📋 Job Description</div>', unsafe_allow_html=True)
    job_description = st.text_area(
        "Job Description",
        placeholder="Paste the full job description here…",
        height=210,
        label_visibility="collapsed",
        key="jd_input",
    )

st.markdown("<br>", unsafe_allow_html=True)
analyze_btn = st.button("🚀 Analyze Resume", key="analyze_btn")

# ─────────────────────────────────────────────
# Analysis Logic
# ─────────────────────────────────────────────
if analyze_btn:
    if not uploaded_file:
        st.warning("⚠️ Please upload a PDF resume.")
        st.stop()
    if not job_description.strip():
        st.warning("⚠️ Please paste a job description to enable ATS matching.")
        st.stop()
    if provider == "groq" and not groq_api_key.strip():
        st.error("❌ Groq API key is required. Add it in the sidebar or switch to Ollama.")
        st.stop()

    # Step 1: Extract text
    with st.spinner("📖 Extracting resume text…"):
        resume_text = extract_text(uploaded_file)

    if resume_text.startswith("[Error]") or resume_text.startswith("[Warning]"):
        st.error(resume_text)
        st.stop()

    st.divider()
    result_col1, result_col2 = st.columns([1, 2], gap="large")

    # Step 2: ATS Score
    with result_col1:
        with st.spinner("� Calculating ATS score…"):
            ats_score, missing_keywords = calculate_similarity(resume_text, job_description)

        if ats_score >= 70:
            score_color, score_emoji, verdict = "#34d399", "🟢", "Strong Match"
        elif ats_score >= 40:
            score_color, score_emoji, verdict = "#fbbf24", "🟡", "Moderate Match"
        else:
            score_color, score_emoji, verdict = "#f87171", "🔴", "Weak Match"

        st.markdown(
            f"""<div class="glass-card" style="text-align:center;">
                <div class="section-label">ATS Match Score</div>
                <div class="score-badge" style="color:{score_color};">{ats_score}%</div>
                <div class="score-label">{score_emoji} {verdict}</div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.progress(int(ats_score))

        # Missing Keywords
        if missing_keywords:
            chips = "".join(f'<span class="chip">{kw}</span>' for kw in missing_keywords)
            st.markdown(
                f'<div class="glass-card"><div class="section-label">🔑 Missing Keywords</div>'
                f'<p style="color:#94a3b8;font-size:0.82rem;margin-bottom:0.6rem;">'
                f'Add these from the job description:</p>{chips}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="glass-card"><div class="section-label">🔑 Missing Keywords</div>'
                '<p style="color:#34d399;">✅ No major missing keywords!</p></div>',
                unsafe_allow_html=True,
            )

    # Step 3: AI Suggestions
    with result_col2:
        model_label = "Groq (llama3-8b)" if provider == "groq" else "Ollama (phi3)"
        with st.spinner(f"🤖 Generating suggestions via {model_label}… (may take up to a minute)"):
            ai_suggestions = improve_resume(
                resume_text,
                provider=provider,
                groq_api_key=groq_api_key,
            )

        st.markdown('<div class="section-label">🤖 AI Improvement Suggestions</div>', unsafe_allow_html=True)
        if ai_suggestions.startswith("❌"):
            st.error(ai_suggestions)
        else:
            st.markdown(
                f'<div class="glass-card">{ai_suggestions}</div>',
                unsafe_allow_html=True,
            )

    # Extracted text expander
    st.divider()
    with st.expander("🔍 View Extracted Resume Text"):
        st.text_area("Extracted Text", value=resume_text, height=280,
                     label_visibility="collapsed", disabled=True)

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    """<div style="text-align:center; color:#475569; font-size:0.78rem;">
        Powered by <strong style="color:#a78bfa;">Groq / Ollama phi3</strong> &nbsp;|&nbsp;
        Built with <strong style="color:#38bdf8;">Streamlit</strong> &nbsp;|&nbsp;
        ATS via <strong style="color:#34d399;">scikit-learn TF-IDF</strong>
    </div>""",
    unsafe_allow_html=True,
)
