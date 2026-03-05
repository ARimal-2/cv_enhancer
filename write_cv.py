"""
write_cv.py — "Write CV with AI" Streamlit page.
Users write each section freely; AI suggests on request.
Text is NEVER overwritten automatically — users pick 1 line, 2 lines, or all.
"""
import re
import streamlit as st
from ai_writer import suggest_for_section
from ats_matcher import calculate_similarity

# CV sections: (state_key, display_name, placeholder)
SECTIONS = [
    ("summary",       "📋 Summary",              "Write a 2–4 sentence professional summary…"),
    ("skills",        "🛠 Skills",                "List your technical skills, tools, languages, frameworks…"),
    ("experience",    "💼 Experience / Projects", "Describe work experience or projects. One bullet per line…"),
    ("education",     "🎓 Education",             "Add degrees, institutions, graduation years…"),
    ("certifications","🏆 Certifications",         "List certifications, online courses, achievements…"),
]

SECTION_NAME_MAP = {
    "summary":        "Summary",
    "skills":         "Skills",
    "experience":     "Experience / Projects",
    "education":      "Education",
    "certifications": "Certifications",
}


def _init_state():
    """Initialize session state for all CV sections."""
    for key, _, _ in SECTIONS:
        st.session_state.setdefault(f"cv_{key}", "")
        st.session_state.setdefault(f"cv_{key}_history", [])
        st.session_state.setdefault(f"cv_{key}_suggestion", None)


def _parse_bullets(text: str) -> list:
    """Extract clean lines from AI suggestion text, stripping bullet markers."""
    lines = []
    for raw in text.split("\n"):
        cleaned = re.sub(r"^[•\-\*\d]+[.):\s]*", "", raw.strip()).strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def _append_lines(key: str, lines: list):
    """Save undo snapshot, append chosen lines to section, clear suggestion."""
    current = st.session_state[f"cv_{key}"]
    st.session_state[f"cv_{key}_history"].append(current)
    added = "\n".join(f"• {ln}" for ln in lines)
    st.session_state[f"cv_{key}"] = (current + "\n" + added).strip()
    st.session_state[f"cv_{key}_suggestion"] = None


def _render_section(key, display_name, placeholder, role, language, provider, groq_api_key, jd_text):
    """Render one CV section: header controls, editor column, suggestion column."""
    section_name = SECTION_NAME_MAP[key]

    # ── Row: title + undo/reset ───────────────────────────────────────────────
    h_col, undo_col, reset_col = st.columns([6, 1, 1])
    with h_col:
        st.markdown(f'<div class="section-label" style="font-size:0.9rem;">{display_name}</div>',
                    unsafe_allow_html=True)
    with undo_col:
        if st.button("↩ Undo", key=f"undo_{key}", use_container_width=True):
            history = st.session_state[f"cv_{key}_history"]
            if history:
                st.session_state[f"cv_{key}"] = history.pop()
                st.session_state[f"cv_{key}_suggestion"] = None
                st.rerun()
    with reset_col:
        if st.button("🗑 Reset", key=f"reset_{key}", use_container_width=True):
            st.session_state[f"cv_{key}_history"].append(st.session_state[f"cv_{key}"])
            st.session_state[f"cv_{key}"] = ""
            st.session_state[f"cv_{key}_suggestion"] = None
            st.rerun()

    # ── Two-column layout: editor | suggestion ───────────────────────────────
    edit_col, sugg_col = st.columns([1, 1], gap="medium")

    with edit_col:
        # Text area — widget key == session state key so AI mutations apply on rerun
        st.text_area(
            display_name,
            key=f"cv_{key}",
            height=180,
            placeholder=placeholder,
            label_visibility="collapsed",
        )

        # Optional ATS score for this section
        current_text = st.session_state[f"cv_{key}"]
        if jd_text.strip() and current_text.strip():
            score, _ = calculate_similarity(current_text, jd_text)
            color = "#34d399" if score >= 70 else "#fbbf24" if score >= 40 else "#f87171"
            st.markdown(
                f'<p style="font-size:0.78rem;color:{color};margin:0.1rem 0 0.4rem;">'
                f'📊 Section ATS: <strong>{score}%</strong></p>',
                unsafe_allow_html=True,
            )

        # Ask AI button
        if st.button(f"🤖 Ask AI for {section_name} suggestions", key=f"ai_{key}", use_container_width=True):
            with st.spinner(f"Getting suggestions for {section_name}…"):
                result = suggest_for_section(
                    section_name=section_name,
                    current_text=st.session_state[f"cv_{key}"],
                    role=role,
                    language=language,
                    provider=provider,
                    groq_api_key=groq_api_key,
                )
            st.session_state[f"cv_{key}_suggestion"] = result
            st.rerun()

    with sugg_col:
        suggestion = st.session_state[f"cv_{key}_suggestion"]

        if suggestion is None:
            # Empty state placeholder
            st.markdown(
                '<div class="glass-card" style="min-height:180px;display:flex;'
                'align-items:center;justify-content:center;text-align:center;">'
                '<p style="color:#475569;font-size:0.85rem;">'
                '💡 AI suggestions appear here.<br>Click <strong>Ask AI</strong> to get started.</p>'
                '</div>',
                unsafe_allow_html=True,
            )

        elif suggestion.startswith("❌"):
            st.error(suggestion)

        else:
            # Format bullets nicely
            formatted = "<br>".join(
                f'<span style="color:#a78bfa;">•</span> {ln}'
                for ln in _parse_bullets(suggestion)
            ) or suggestion.replace("\n", "<br>")

            st.markdown(
                f'<div class="glass-card">'
                f'<div class="section-label" style="margin-bottom:0.4rem;">💡 AI Suggestion</div>'
                f'<div style="color:#e2e8f0;font-size:0.84rem;line-height:1.9;">{formatted}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Add controls
            bullets = _parse_bullets(suggestion)
            st.markdown(
                '<p style="color:#94a3b8;font-size:0.78rem;margin:0.3rem 0 0.2rem;">'
                '<strong>How much would you like to add?</strong></p>',
                unsafe_allow_html=True,
            )
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if st.button("➕ 1 line", key=f"add1_{key}", use_container_width=True) and bullets:
                    _append_lines(key, bullets[:1])
                    st.rerun()
            with b2:
                if st.button("➕ 2 lines", key=f"add2_{key}", use_container_width=True) and bullets:
                    _append_lines(key, bullets[:2])
                    st.rerun()
            with b3:
                if st.button("➕ All", key=f"addall_{key}", use_container_width=True) and bullets:
                    _append_lines(key, bullets)
                    st.rerun()
            with b4:
                if st.button("✖ Dismiss", key=f"dismiss_{key}", use_container_width=True):
                    st.session_state[f"cv_{key}_suggestion"] = None
                    st.rerun()


def _build_cv_text() -> str:
    """Compile all non-empty sections into a plain-text CV string for download."""
    lines = []
    for key, display_name, _ in SECTIONS:
        text = st.session_state.get(f"cv_{key}", "").strip()
        if text:
            clean = re.sub(r"[^\w\s/]", "", display_name).strip().upper()
            lines += ["=" * 50, clean, "=" * 50, text, ""]
    return "\n".join(lines).strip()


def render_write_cv(provider, groq_api_key, language, target_role, jd_text):
    """
    Main entry point — called from app.py inside the Write CV tab.

    Args:
        provider:      "groq" or "ollama"
        groq_api_key:  Groq API key string
        language:      "English" or "Nepali"
        target_role:   Optional target job role string
        jd_text:       Optional job description for per-section ATS scoring
    """
    _init_state()

    # Intro text
    st.markdown(
        '<p style="color:#94a3b8;font-size:0.93rem;margin-bottom:1.2rem;">'
        'Write each section freely. Click <strong style="color:#a78bfa;">Ask AI</strong> '
        'to get bullet-point suggestions — your text is '
        '<em>never overwritten automatically</em>. '
        'Choose how much of each suggestion to accept, then keep editing.</p>',
        unsafe_allow_html=True,
    )

    # Active settings chips
    chips = []
    if target_role.strip():
        chips.append(f'🎯 {target_role}')
    chips.append(f'🌐 {language}')
    provider_label = "☁️ Groq" if provider == "groq" else "🖥️ Ollama · phi3"
    chips.append(provider_label)
    chip_html = "".join(f'<span class="chip">{c}</span>' for c in chips)
    st.markdown(f'<div style="margin-bottom:1.25rem;">{chip_html}</div>', unsafe_allow_html=True)

    # Render each section inside a glass card
    for key, display_name, placeholder in SECTIONS:
        st.markdown('<div class="glass-card" style="padding:1.2rem 1.5rem;">', unsafe_allow_html=True)
        _render_section(key, display_name, placeholder, target_role, language,
                        provider, groq_api_key, jd_text)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("")  # spacing

    # Export
    st.markdown("---")
    st.markdown('<div class="section-label" style="font-size:0.9rem;">📥 Export Your CV</div>',
                unsafe_allow_html=True)
    cv_text = _build_cv_text()
    if cv_text:
        dl_col, prev_col = st.columns([1, 3])
        with dl_col:
            st.download_button(
                label="⬇️ Download as TXT",
                data=cv_text,
                file_name="my_cv.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with prev_col:
            with st.expander("👀 Preview full CV"):
                st.text_area("preview", value=cv_text, height=280,
                             label_visibility="collapsed", disabled=True)
    else:
        st.info("Start writing your CV above to enable export.")
