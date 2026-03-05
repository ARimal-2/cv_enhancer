"""
app.py — AI Resume Improver · Main Streamlit Application
Two features selectable via tabs:
  • CV Enhancer    — upload a PDF, get AI improvements + ATS score
  • Write CV with AI — write each section from scratch with AI assistance
Run: streamlit run app.py
"""

import os
import streamlit as st

from parser import extract_text
from ai_engine import improve_resume
from ats_matcher import calculate_similarity
from write_cv import render_write_cv
from cv_extraction_ui import render_cv_extraction

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Resume Improver",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Global CSS — dark glassmorphism design
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); min-height: 100vh; }

[data-testid="stSidebar"] {
    background: rgba(15,12,41,0.90) !important;
    border-right: 1px solid rgba(255,255,255,0.08);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
    background: rgba(255,255,255,0.03);
    border-radius: 12px;
    padding: 0.35rem;
    border: 1px solid rgba(255,255,255,0.08);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    color: #94a3b8;
    font-weight: 500;
    padding: 0.45rem 1.2rem;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #7c3aed, #2563eb) !important;
    color: white !important;
}

/* Typography */
.hero-title {
    text-align: center;
    font-size: 2.6rem;
    font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #38bdf8, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.2rem;
}
.hero-subtitle { text-align: center; color: #94a3b8; font-size: 0.97rem; margin-bottom: 1.5rem; }
.section-label {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: #a78bfa; margin-bottom: 0.5rem;
}

/* Glass card */
.glass-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 1.4rem 1.75rem;
    backdrop-filter: blur(10px);
    margin-bottom: 1rem;
}

/* Score badge */
.score-badge { display: inline-block; font-size: 3rem; font-weight: 700; line-height: 1; }
.score-label { font-size: 0.88rem; color: #94a3b8; margin-top: 0.2rem; }

/* Keyword chips */
.chip {
    display: inline-block;
    background: rgba(167,139,250,0.15);
    border: 1px solid rgba(167,139,250,0.4);
    color: #c4b5fd;
    border-radius: 999px;
    padding: 0.22rem 0.7rem;
    font-size: 0.78rem;
    font-weight: 500;
    margin: 0.18rem;
}
.provider-badge {
    display: inline-block; padding: 0.2rem 0.65rem;
    border-radius: 999px; font-size: 0.75rem; font-weight: 600; margin-bottom: 0.75rem;
}

/* Inputs */
.stTextArea textarea {
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
}
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #2563eb) !important;
    color: white !important; border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
hr { border-color: rgba(255,255,255,0.08); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar — shared + feature-specific settings
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
    )

    groq_api_key = ""
    if provider == "groq":
        st.markdown("#### 🔑 Groq API Key")
        env_key = os.environ.get("GROQ_API_KEY", "")
        groq_api_key = st.text_input(
            "Groq API Key", value=env_key, type="password",
            placeholder="gsk_...", label_visibility="collapsed", key="groq_key",
        )
        st.markdown("Get a **free** key → [console.groq.com](https://console.groq.com)")
    else:
        st.info("Make sure Ollama is running:\n```\nollama serve\nollama pull phi3\n```")

    # ── Write CV specific settings ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### ✍️ CV Writer Settings")
    language = st.selectbox("🌐 Language", ["English", "Nepali"], key="cv_language")
    target_role = st.text_input("🎯 Target Role (optional)",
                                placeholder="e.g. Data Scientist", key="cv_target_role")

    show_section_ats = st.checkbox("📊 Show ATS score per section", key="cv_show_ats")
    jd_for_cv = ""
    if show_section_ats:
        st.markdown("Paste job description:")
        jd_for_cv = st.text_area("JD for CV sections", height=130,
                                  label_visibility="collapsed", key="cv_jd_input")

    # ── About ─────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📘 About")
    st.markdown(
        "- 📄 **PDF Parser** — pdfplumber\n"
        "- 🤖 **AI** — Groq or Ollama\n"
        "- 📊 **ATS** — scikit-learn TF-IDF\n"
        "- ✍️ **CV Writer** — AI-assisted drafting\n"
        "- 📦 **CV Extractor** — AI structured data"
    )

# ─────────────────────────────────────────────
# Hero header
# ─────────────────────────────────────────────
st.markdown('<h1 class="hero-title">📄 AI Resume Improver</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-subtitle">Enhance an existing resume · or write a new CV from scratch — powered by AI</p>',
    unsafe_allow_html=True,
)

# Provider badge
badge_color = "#38bdf8" if provider == "groq" else "#a78bfa"
badge_label = "☁️ Groq Cloud" if provider == "groq" else "🖥️ Ollama · phi3"
st.markdown(
    f'<div style="text-align:center;margin-bottom:1.25rem;">'
    f'<span class="provider-badge" style="background:rgba(56,189,248,0.12);'
    f'border:1px solid {badge_color};color:{badge_color};">{badge_label}</span></div>',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab_enhancer, tab_writer, tab_extractor = st.tabs([
    "📄  CV Enhancer", 
    "✍️  Write CV with AI", 
    "📦  CV Extractor"
])


# ══════════════════════════════════════════════
# Tab 1 — CV Enhancer (original feature)
# ══════════════════════════════════════════════
with tab_enhancer:
    st.markdown(
        '<p style="color:#94a3b8;font-size:0.93rem;margin-bottom:1.25rem;">'
        'Upload a PDF resume and paste a job description to get an ATS score '
        'and AI-powered improvement suggestions.</p>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown('<div class="section-label">📎 Upload Resume (PDF)</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Resume PDF", type=["pdf"],
            label_visibility="collapsed", key="resume_uploader",
        )
        if uploaded_file:
            st.success(f"✅ Loaded: **{uploaded_file.name}**")

    with col_right:
        st.markdown('<div class="section-label">📋 Job Description</div>', unsafe_allow_html=True)
        job_description = st.text_area(
            "Job Description", placeholder="Paste the full job description here…",
            height=210, label_visibility="collapsed", key="jd_input",
        )

    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🚀 Analyze Resume", key="analyze_btn")

    if analyze_btn:
        if not uploaded_file:
            st.warning("⚠️ Please upload a PDF resume.")
            st.stop()
        if not job_description.strip():
            st.warning("⚠️ Please paste a job description.")
            st.stop()
        if provider == "groq" and not groq_api_key.strip():
            st.error("❌ A Groq API key is required. Add it in the sidebar.")
            st.stop()

        with st.spinner("📖 Extracting resume text…"):
            resume_text = extract_text(uploaded_file)

        if resume_text.startswith("[Error]") or resume_text.startswith("[Warning]"):
            st.error(resume_text)
            st.stop()

        st.divider()
        res_col1, res_col2 = st.columns([1, 2], gap="large")

        # ATS Score
        with res_col1:
            with st.spinner("📊 Calculating ATS score…"):
                ats_score, missing_kw = calculate_similarity(resume_text, job_description)

            if ats_score >= 70:
                sc, se, sv = "#34d399", "🟢", "Strong Match"
            elif ats_score >= 40:
                sc, se, sv = "#fbbf24", "🟡", "Moderate Match"
            else:
                sc, se, sv = "#f87171", "🔴", "Weak Match"

            st.markdown(
                f'<div class="glass-card" style="text-align:center;">'
                f'<div class="section-label">ATS Match Score</div>'
                f'<div class="score-badge" style="color:{sc};">{ats_score}%</div>'
                f'<div class="score-label">{se} {sv}</div></div>',
                unsafe_allow_html=True,
            )
            st.progress(int(ats_score))

            if missing_kw:
                chips = "".join(f'<span class="chip">{kw}</span>' for kw in missing_kw)
                st.markdown(
                    f'<div class="glass-card"><div class="section-label">🔑 Missing Keywords</div>'
                    f'<p style="color:#94a3b8;font-size:0.82rem;margin-bottom:0.5rem;">'
                    f'Consider adding these from the job description:</p>{chips}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="glass-card"><div class="section-label">🔑 Missing Keywords</div>'
                    '<p style="color:#34d399;">✅ No major missing keywords!</p></div>',
                    unsafe_allow_html=True,
                )

        # AI Suggestions
        with res_col2:
            model_lbl = "Groq (llama-3.1-8b)" if provider == "groq" else "Ollama (phi3)"
            with st.spinner(f"🤖 Generating suggestions via {model_lbl}…"):
                ai_suggestions = improve_resume(resume_text, provider=provider, groq_api_key=groq_api_key)

            st.markdown('<div class="section-label">🤖 AI Improvement Suggestions</div>',
                        unsafe_allow_html=True)
            if ai_suggestions.startswith("❌"):
                st.error(ai_suggestions)
            else:
                st.markdown(f'<div class="glass-card">{ai_suggestions}</div>', unsafe_allow_html=True)

        st.divider()
        with st.expander("🔍 View Extracted Resume Text"):
            st.text_area("Extracted", value=resume_text, height=260,
                         label_visibility="collapsed", disabled=True)


# ══════════════════════════════════════════════
# Tab 2 — Write CV with AI
# ══════════════════════════════════════════════
with tab_writer:
    render_write_cv(
        provider=provider,
        groq_api_key=groq_api_key,
        language=language,
        target_role=target_role,
        jd_text=jd_for_cv,
    )

# ══════════════════════════════════════════════
# Tab 3 — CV Extractor
# ══════════════════════════════════════════════
with tab_extractor:
    render_cv_extraction(
        provider=provider,
        groq_api_key=groq_api_key
    )

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div style="text-align:center;color:#475569;font-size:0.78rem;">'
    'Powered by <strong style="color:#a78bfa;">Groq / Ollama phi3</strong> &nbsp;|&nbsp;'
    'Built with <strong style="color:#38bdf8;">Streamlit</strong> &nbsp;|&nbsp;'
    'ATS via <strong style="color:#34d399;">scikit-learn</strong>'
    '</div>',
    unsafe_allow_html=True,
)
