"""
cv_extraction_ui.py
Streamlit page for the "CV Extractor" tab.
Uploads a PDF, parses it, extracts structured JSON via AI,
then displays it in a rich, readable UI with a JSON download.
"""
import json
import streamlit as st
from parser import extract_text
from cv_extractor import extract_cv_data


# ── Helpers ───────────────────────────────────────────────────────────────────
def _v(value, fallback="—"):
    """Return value or fallback when None / empty."""
    if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
        return fallback
    return value


def _chip(label, color="#a78bfa"):
    return (
        f'<span class="chip" style="border-color:{color};'
        f'color:{color};background:rgba(167,139,250,0.08);">{label}</span>'
    )


def _card(content_html):
    return f'<div class="glass-card">{content_html}</div>'


def _section_label(text):
    return f'<div class="section-label" style="font-size:0.82rem;margin-bottom:0.5rem;">{text}</div>'


# ── Section renderers ─────────────────────────────────────────────────────────
def _render_contact(data):
    first  = _v(data.get("first_name"), "")
    last   = _v(data.get("last_name"),  "")
    name   = f"{first} {last}".strip() or "—"
    email  = data.get("email")
    phone  = data.get("phone_number")
    li     = data.get("linkedin")
    gh     = data.get("github")

    rows = [
        _section_label("👤 Contact Information"),
        f'<p style="color:#e2e8f0;font-size:1.25rem;font-weight:700;margin:0.2rem 0 0.5rem;">{name}</p>',
    ]
    if email: rows.append(f'<p style="color:#94a3b8;margin:0.15rem 0;">📧 {email}</p>')
    if phone: rows.append(f'<p style="color:#94a3b8;margin:0.15rem 0;">📞 {phone}</p>')
    if li:    rows.append(f'<p style="margin:0.15rem 0;">🔗 <a href="{li}" target="_blank" style="color:#38bdf8;">LinkedIn Profile</a></p>')
    if gh:    rows.append(f'<p style="margin:0.15rem 0;">💻 <a href="{gh}" target="_blank" style="color:#38bdf8;">GitHub Profile</a></p>')
    return _card("".join(rows))


def _render_summary(data):
    summary = _v(data.get("professional_summary"))
    return _card(
        _section_label("📋 Professional Summary")
        + f'<p style="color:#e2e8f0;line-height:1.85;font-size:0.9rem;">{summary}</p>'
    )


def _render_skills(data):
    skills = data.get("technical_skills") or []
    if not skills:
        return ""
    chips = "".join(_chip(s) for s in skills)
    return _card(_section_label("🛠 Technical Skills") + f'<div style="margin-top:0.3rem;">{chips}</div>')


def _render_experience(data):
    experiences = data.get("professional_experience") or []
    blocks = []
    for exp in experiences:
        title    = _v(exp.get("job_title"))
        company  = _v(exp.get("company"))
        location = _v(exp.get("location"))
        start    = _v(exp.get("start_date"))
        end      = _v(exp.get("end_date"))
        acts     = exp.get("achievements") or []

        ach_html = "".join(
            f'<li style="color:#cbd5e1;margin:0.3rem 0;line-height:1.6;">{a}</li>'
            for a in acts
        )
        blocks.append(
            '<div class="glass-card">'
            '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">'
            f'<div><p style="color:#e2e8f0;font-weight:600;font-size:1rem;margin:0;">{title}</p>'
            f'<p style="color:#a78bfa;font-size:0.87rem;margin:0.15rem 0;">{company} · {location}</p></div>'
            f'<span class="chip" style="white-space:nowrap;">{start} → {end}</span></div>'
            + (f'<ul style="margin:0.6rem 0 0;padding-left:1.2rem;">{ach_html}</ul>' if ach_html else "")
            + '</div>'
        )
    return "".join(blocks)


def _render_projects(data):
    projects = data.get("projects") or []
    if not projects:
        return []
    cards = []
    for proj in projects:
        techs       = proj.get("technologies_used") or []
        impact      = proj.get("impact_metrics")
        tech_html   = "".join(_chip(t, "#38bdf8") for t in techs)
        impact_html = f'<p style="color:#34d399;font-size:0.8rem;margin:0.4rem 0 0;">📈 {impact}</p>' if impact else ""
        cards.append(
            _card(
                f'<p style="color:#e2e8f0;font-weight:600;font-size:0.97rem;margin:0 0 0.3rem;">'
                f'{_v(proj.get("project_name"))}</p>'
                f'<p style="color:#94a3b8;font-size:0.84rem;line-height:1.65;">{_v(proj.get("description"))}</p>'
                + (f'<div style="margin-top:0.4rem;">{tech_html}</div>' if tech_html else "")
                + impact_html
            )
        )
    return cards


def _render_education(data):
    edu_list = data.get("education") or []
    if not edu_list:
        return ""
    rows = [_section_label("🎓 Education")]
    for i, ed in enumerate(edu_list):
        sy  = ed.get("start_year") or ""
        ey  = ed.get("end_year")   or ""
        yr  = f"{sy} – {ey}".strip(" –") if sy or ey else ""
        loc = ed.get("location") or ""
        sep = '<hr style="border-color:rgba(255,255,255,0.06);margin:0.6rem 0;">' if i else ""
        rows.append(
            sep
            + f'<p style="color:#e2e8f0;font-weight:600;margin:0;">{_v(ed.get("degree"))}</p>'
            f'<p style="color:#a78bfa;font-size:0.86rem;margin:0.1rem 0;">{_v(ed.get("university"))}</p>'
            + (f'<p style="color:#64748b;font-size:0.78rem;margin:0;">{loc}{"  " if loc and yr else ""}{yr}</p>'
               if loc or yr else "")
        )
    return _card("".join(rows))


def _render_certs_langs(data):
    certs = data.get("certifications") or []
    langs = data.get("languages")     or []
    if not certs and not langs:
        return ""
    content = _section_label("🏆 Certifications & Languages")
    if certs:
        content += "".join(
            f'<p style="color:#cbd5e1;font-size:0.85rem;margin:0.2rem 0;">✅ {c}</p>'
            for c in certs
        )
    if langs:
        content += _section_label("🌐 Languages") + "".join(_chip(l, "#34d399") for l in langs)
    return _card(content)


# ── Main render ───────────────────────────────────────────────────────────────
def render_cv_extraction(provider: str, groq_api_key: str):
    """Entry point called from app.py inside the CV Extractor tab."""

    st.markdown(
        '<p style="color:#94a3b8;font-size:0.93rem;margin-bottom:1.25rem;">'
        'Upload a PDF resume and extract every field — contact details, experience, '
        'skills, projects, education — as clean, structured JSON ready to use programmatically.</p>',
        unsafe_allow_html=True,
    )

    # Upload
    st.markdown('<div class="section-label">📎 Upload Resume (PDF)</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Resume PDF", type=["pdf"],
        label_visibility="collapsed", key="extract_uploader",
    )
    if uploaded:
        st.success(f"✅ Loaded: **{uploaded.name}**")

    st.markdown("<br>", unsafe_allow_html=True)
    extract_btn = st.button("🔍 Extract CV Data", key="extract_btn", use_container_width=False)

    if not extract_btn:
        return

    # Validate
    if not uploaded:
        st.warning("⚠️ Please upload a PDF resume first.")
        return
    if provider == "groq" and not groq_api_key.strip():
        st.error("❌ Groq API key required. Add it in the sidebar.")
        return

    # Step 1 — Extract text
    with st.spinner("📖 Reading PDF…"):
        resume_text = extract_text(uploaded)
    if resume_text.startswith("[Error]") or resume_text.startswith("[Warning]"):
        st.error(resume_text)
        return

    # Step 2 — AI extraction
    with st.spinner("🤖 Extracting structured data with AI… (up to ~40 seconds)"):
        data, error = extract_cv_data(resume_text, provider=provider, groq_api_key=groq_api_key)

    if error:
        st.error(error)
        return

    st.divider()

    # ── Render extracted data ─────────────────────────────────────────────────

    # Row 1: Contact | Summary
    c1, c2 = st.columns([1, 2], gap="large")
    with c1:
        st.markdown(_render_contact(data), unsafe_allow_html=True)
    with c2:
        st.markdown(_render_summary(data), unsafe_allow_html=True)

    # Skills
    skills_html = _render_skills(data)
    if skills_html:
        st.markdown(skills_html, unsafe_allow_html=True)

    # Experience
    exp_html = _render_experience(data)
    if exp_html:
        st.markdown('<div class="section-label" style="font-size:0.88rem;margin-top:0.25rem;">💼 Professional Experience</div>',
                    unsafe_allow_html=True)
        st.markdown(exp_html, unsafe_allow_html=True)

    # Projects (responsive grid)
    proj_cards = _render_projects(data)
    if proj_cards:
        st.markdown('<div class="section-label" style="font-size:0.88rem;margin-top:0.25rem;">🚀 Projects</div>',
                    unsafe_allow_html=True)
        n_cols = min(len(proj_cards), 2)
        proj_cols = st.columns(n_cols, gap="medium")
        for i, card_html in enumerate(proj_cards):
            with proj_cols[i % n_cols]:
                st.markdown(card_html, unsafe_allow_html=True)

    # Education | Certifications & Languages
    edu_col, cert_col = st.columns([1, 1], gap="medium")
    with edu_col:
        edu_html = _render_education(data)
        if edu_html:
            st.markdown(edu_html, unsafe_allow_html=True)
    with cert_col:
        cl_html = _render_certs_langs(data)
        if cl_html:
            st.markdown(cl_html, unsafe_allow_html=True)

    # ── JSON export ───────────────────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="section-label">📦 Raw JSON Output</div>', unsafe_allow_html=True)
    json_str = json.dumps(data, indent=2, ensure_ascii=False)

    dl_col, _ = st.columns([1, 4])
    with dl_col:
        st.download_button(
            label="⬇️ Download JSON",
            data=json_str,
            file_name="cv_extracted.json",
            mime="application/json",
            use_container_width=True,
        )

    with st.expander("🔍 View Full JSON"):
        st.code(json_str, language="json")
