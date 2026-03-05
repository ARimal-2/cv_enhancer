"""
write_cv.py — "Write CV with AI" Streamlit page.
Users write each section freely; AI suggests on request.
Text is NEVER overwritten automatically — users pick 1 line, 2 lines, or all.
"""
import re
import json
import streamlit as st
from fpdf import FPDF
from ai_writer import suggest_for_section
from ats_matcher import calculate_similarity

# CV Section configuration (used for general rendering if needed, 
# but many are now handled individually for more control)
SECTIONS = [
    ("summary",       "📋 Summary",              "Write a 2–4 sentence professional summary…"),
    ("skills",        "🛠 Skills",                "List your technical skills (e.g., Python, SQL, Spark)…"),
    ("certifications","🏆 Certifications",         "List certifications, online courses…"),
    ("languages",     "🌐 Languages",               "e.g., English – Professional, Nepali – Native"),
]

SECTION_NAME_MAP = {
    "summary":        "Summary",
    "skills":         "Skills",
    "experience":     "Experience / Projects",
    "education":      "Education",
    "certifications": "Certifications",
    "languages":      "Languages",
}


def _init_state():
    """Initialize session state for all CV sections including structured data."""
    # Personal Info
    st.session_state.setdefault("cv_personal", {
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "linkedin": "",
        "github": "",
        "profile_image_url": ""
    })
    
    # Generic sections
    for key in ["summary", "skills", "certifications", "languages"]:
        st.session_state.setdefault(f"cv_{key}", "")
        st.session_state.setdefault(f"cv_{key}_history", [])
        st.session_state.setdefault(f"cv_{key}_suggestion", None)
    
    # Repeatable sections
    st.session_state.setdefault("cv_experience", [])
    st.session_state.setdefault("cv_education", [])
    
    # Suggestion state for repeatable sections is usually handled per-item 
    # or via a temporary buffer. For simplicity, we'll keep it per segment.
    st.session_state.setdefault("cv_exp_suggestion", None)
    st.session_state.setdefault("cv_edu_suggestion", None)


def _parse_bullets(text: str) -> list:
    """Extract clean lines from AI suggestion text, stripping bullet markers."""
    if not text: return []
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
    if current.strip():
        st.session_state[f"cv_{key}"] = (current + "\n" + added).strip()
    else:
        st.session_state[f"cv_{key}"] = added.strip()
    st.session_state[f"cv_{key}_suggestion"] = None


def _render_personal_info():
    """Render the personal information section with specific input fields."""
    st.markdown('<div class="section-label" style="font-size:0.9rem;">👤 Personal Information</div>', unsafe_allow_html=True)
    
    p = st.session_state.cv_personal
    col1, col2 = st.columns(2)
    with col1:
        p["first_name"] = st.text_input("First Name (mandatory) *", value=p["first_name"])
        p["email"] = st.text_input("Email (optional)", value=p["email"])
        p["linkedin"] = st.text_input("LinkedIn (optional)", value=p["linkedin"])
    with col2:
        p["last_name"] = st.text_input("Last Name (mandatory) *", value=p["last_name"])
        p["phone"] = st.text_input("Phone Number (optional)", value=p["phone"])
        p["github"] = st.text_input("GitHub (optional)", value=p["github"])
    
    p["profile_image_url"] = st.text_input("Profile Image URL or Upload Field Placeholder", value=p["profile_image_url"])
    st.session_state.cv_personal = p


def _render_repeating_section(section_type, role, language, provider, groq_api_key):
    """Render repeatable sections for Experience or Education."""
    title = SECTION_NAME_MAP[section_type]
    icon = "💼" if section_type == "experience" else "🎓"
    st.markdown(f'<div class="section-label" style="font-size:0.9rem;">{icon} {title}</div>', unsafe_allow_html=True)
    
    items = st.session_state[f"cv_{section_type}"]
    
    # Render existing items
    for idx, item in enumerate(items):
        with st.expander(f"{item.get('title', item.get('degree', 'Entry'))} @ {item.get('company', item.get('institution', 'Organization'))}", expanded=True):
            cols = st.columns([3, 3, 1])
            if section_type == "experience":
                item["title"] = cols[0].text_input("Job Title / Project Name *", value=item.get("title", ""), key=f"{section_type}_t_{idx}")
                item["company"] = cols[1].text_input("Company / Organization *", value=item.get("company", ""), key=f"{section_type}_c_{idx}")
                
                loc_cols = st.columns(3)
                item["location"] = loc_cols[0].text_input("Location", value=item.get("location", ""), key=f"{section_type}_l_{idx}")
                item["start_date"] = loc_cols[1].text_input("Start Date", value=item.get("start_date", ""), key=f"{section_type}_sd_{idx}")
                item["end_date"] = loc_cols[2].text_input("End Date / 'Present'", value=item.get("end_date", ""), key=f"{section_type}_ed_{idx}")
                
                item["bullets"] = st.text_area("Achievements / Responsibilities (bullets)", value=item.get("bullets", ""), 
                                               height=150, key=f"{section_type}_b_{idx}")
            else:
                item["degree"] = cols[0].text_input("Degree *", value=item.get("degree", ""), key=f"{section_type}_d_{idx}")
                item["institution"] = cols[1].text_input("University / Institution *", value=item.get("institution", ""), key=f"{section_type}_i_{idx}")
                
                loc_cols = st.columns(3)
                item["location"] = loc_cols[0].text_input("Location", value=item.get("location", ""), key=f"{section_type}_l_{idx}")
                item["start_year"] = loc_cols[1].text_input("Start Year", value=item.get("start_year", ""), key=f"{section_type}_sy_{idx}")
                item["end_year"] = loc_cols[2].text_input("End Year", value=item.get("end_year", ""), key=f"{section_type}_ey_{idx}")

            # AI Suggestion for this specific item
            if st.button(f"🤖 Ask AI to polish this {title[:-1] if title.endswith('s') else title}", key=f"ai_{section_type}_{idx}"):
                with st.spinner("Polishing..."):
                    input_text = item.get("bullets", f"{item.get('degree')} at {item.get('institution')}")
                    result = suggest_for_section(
                        section_name=title,
                        current_text=input_text,
                        role=role,
                        language=language,
                        provider=provider,
                        groq_api_key=groq_api_key
                    )
                    st.session_state[f"last_sugg_{section_type}_{idx}"] = result
            
            if f"last_sugg_{section_type}_{idx}" in st.session_state:
                sugg = st.session_state[f"last_sugg_{section_type}_{idx}"]
                st.info(f"💡 AI Suggestion:\n\n{sugg}")
                if st.button("Apply Suggestion", key=f"apply_{section_type}_{idx}"):
                    if section_type == "experience":
                        item["bullets"] = sugg
                    else:
                        # For education, AI might return a formatted string. 
                        # This is a bit tricky with structured fields, but let's assume it polishes what's there.
                        st.info("AI suggested a polish. Please review and apply manually if needed, or we can auto-fill if the AI format is stable.")
                    del st.session_state[f"last_sugg_{section_type}_{idx}"]
                    st.rerun()

            if cols[2].button("🗑 Remove", key=f"rm_{section_type}_{idx}"):
                items.pop(idx)
                st.session_state[f"cv_{section_type}"] = items
                st.rerun()

    if st.button(f"➕ Add {title[:-1] if title.endswith('s') else title}", key=f"add_{section_type}"):
        items.append({})
        st.session_state[f"cv_{section_type}"] = items
        st.rerun()


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
                '<p style="color:#ffffff77;font-size:0.85rem;">'
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


def _validate_cv() -> list:
    """Check mandatory fields."""
    errors = []
    p = st.session_state.get("cv_personal", {})
    if not p.get("first_name", "").strip(): errors.append("First Name is mandatory.")
    if not p.get("last_name", "").strip(): errors.append("Last Name is mandatory.")
    if not st.session_state.get("cv_summary", "").strip(): errors.append("Professional Summary is mandatory.")
    
    exp = st.session_state.get("cv_experience", [])
    for i, e in enumerate(exp):
        if not e.get("title", "").strip(): errors.append(f"Experience #{i+1}: Missing Job Title.")
        if not e.get("company", "").strip(): errors.append(f"Experience #{i+1}: Missing Company Name.")
    
    return errors


def _build_cv_text() -> str:
    """Compile structured data into a plain-text CV."""
    p = st.session_state.get("cv_personal", {})
    lines = []
    
    # Header
    name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
    if name:
        lines += [name.upper(), "=" * len(name)]
    
    contacts = [p.get(k) for k in ["email", "phone", "linkedin", "github"] if p.get(k)]
    if contacts:
        lines.append(" | ".join(contacts))
    lines.append("")

    # Summary
    summary = st.session_state.get("cv_summary", "").strip()
    if summary:
        lines += ["SUMMARY", "-" * 7, summary, ""]

    # Experience
    exp = st.session_state.get("cv_experience", [])
    if exp:
        lines += ["EXPERIENCE", "-" * 10]
        for e in exp:
            header = f"{e.get('title', 'Position')} @ {e.get('company', 'Company')}"
            date = f"{e.get('start_date', '')} - {e.get('end_date', 'Present')}"
            lines += [f"{header} ({date})", e.get("location", "")]
            lines += [e.get("bullets", ""), ""]

    # Education
    edu = st.session_state.get("cv_education", [])
    if edu:
        lines += ["EDUCATION", "-" * 9]
        for d in edu:
            lines += [f"{d.get('degree', 'Degree')} - {d.get('institution', 'University')}",
                     f"{d.get('start_year', '')} - {d.get('end_year', '')}", ""]

    # Simple sections
    for key, display_name, _ in SECTIONS:
        if key in ["summary"]: continue # handled
        text = st.session_state.get(f"cv_{key}", "").strip()
        if text:
            clean_title = re.sub(r"[^\w\s/]", "", display_name).strip().upper()
            lines += [clean_title, "-" * len(clean_title), text, ""]

    return "\n".join(lines).strip()


def _build_cv_json() -> str:
    """Export CV data as JSON."""
    data = {
        "personal": st.session_state.cv_personal,
        "summary": st.session_state.cv_summary,
        "experience": st.session_state.cv_experience,
        "education": st.session_state.cv_education,
        "skills": st.session_state.cv_skills,
        "certifications": st.session_state.cv_certifications,
        "languages": st.session_state.cv_languages
    }
    return json.dumps(data, indent=2)


def _build_cv_pdf() -> bytes:
    """Generate a clean, ATS-friendly PDF version of the CV."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    p = st.session_state.cv_personal
    name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
    
    # Font settings
    pdf.set_font("Helvetica", "B", 24)
    if name:
        pdf.cell(0, 15, name.upper(), ln=True, align="C")
    
    pdf.set_font("Helvetica", "", 10)
    contacts = [p.get(k) for k in ["email", "phone", "linkedin", "github"] if p.get(k)]
    if contacts:
        pdf.cell(0, 5, " | ".join(contacts), ln=True, align="C")
    
    pdf.ln(10)
    
    def add_section_header(title):
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, title.upper(), ln=True, fill=True)
        pdf.ln(2)

    # Summary
    summary = st.session_state.get("cv_summary", "").strip()
    if summary:
        add_section_header("Professional Summary")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, summary)
        pdf.ln(5)

    # Experience
    exp = st.session_state.get("cv_experience", [])
    if exp:
        add_section_header("Professional Experience")
        for e in exp:
            pdf.set_font("Helvetica", "B", 12)
            header = f"{e.get('title', 'Position')} @ {e.get('company', 'Company')}"
            pdf.cell(0, 7, header, ln=False)
            pdf.set_font("Helvetica", "I", 10)
            date = f"{e.get('start_date', '')} - {e.get('end_date', 'Present')}"
            pdf.cell(0, 7, date, ln=True, align="R")
            
            pdf.set_font("Helvetica", "", 10)
            if e.get("location"):
                pdf.cell(0, 5, e.get("location"), ln=True)
            
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, e.get("bullets", ""))
            pdf.ln(4)

    # Education
    edu = st.session_state.get("cv_education", [])
    if edu:
        add_section_header("Education")
        for d in edu:
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 7, f"{d.get('degree', 'Degree')}", ln=False)
            pdf.set_font("Helvetica", "", 11)
            pdf.cell(0, 7, f" {d.get('start_year', '')} - {d.get('end_year', '')}", ln=True, align="R")
            pdf.set_font("Helvetica", "I", 11)
            pdf.cell(0, 6, f"{d.get('institution', 'University')}, {d.get('location', '')}", ln=True)
            pdf.ln(3)

    # Other Sections
    for key, display_name, _ in SECTIONS:
        if key == "summary": continue
        text = st.session_state.get(f"cv_{key}", "").strip()
        if text:
            add_section_header(re.sub(r"[^\w\s/]", "", display_name).strip())
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, text)
            pdf.ln(5)

    return pdf.output()


def render_write_cv(provider, groq_api_key, language, target_role, jd_text):
    """
    Main entry point — called from app.py inside the Write CV tab.
    """
    _init_state()

    # Intro text
    st.markdown(
        '<p style="color:#ffffff99;font-size:0.93rem;margin-bottom:1.2rem;">'
        'Complete the fields below. Use <strong style="color:#a78bfa;">Ask AI</strong> '
        'to polish your entries with professional CAR-style suggestions.</p>',
        unsafe_allow_html=True,
    )

    # Active settings chips (role, lang, etc)
    chips = []
    if target_role.strip(): chips.append(f'🎯 {target_role}')
    chips.append(f'🌐 {language}')
    st.markdown(" ".join([f'<span class="chip">{c}</span>' for c in chips]), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # 1. Personal Info
    with st.container(border=True): 
        _render_personal_info()

    # 2. Professional Summary
    with st.container(border=True):
        _render_section("summary", "📋 Professional Summary (mandatory) *", 
                        "Write 2–4 sentences about your career goals and key strengths…",
                        target_role, language, provider, groq_api_key, jd_text)

    # 3. Technical Skills
    with st.container(border=True):
        _render_section("skills", "🛠 Technical Skills", 
                        "Python, SQL, AWS, Machine Learning, Docker...",
                        target_role, language, provider, groq_api_key, jd_text)

    # 4. Experience / Projects
    with st.container(border=True):
        _render_repeating_section("experience", target_role, language, provider, groq_api_key)

    # 5. Education
    with st.container(border=True):
        _render_repeating_section("education", target_role, language, provider, groq_api_key)

    # 6 & 7. Certs & Languages
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            _render_section("certifications", "🏆 Certifications", "AWS Certified Cloud Practitioner...",
                            target_role, language, provider, groq_api_key, jd_text)
    with col_b:
        with st.container(border=True):
            _render_section("languages", "🌐 Languages", "English – Professional, Nepali – Native",
                            target_role, language, provider, groq_api_key, jd_text)

    # Export
    st.markdown("---")
    st.markdown('<div class="section-label" style="font-size:0.9rem;">📥 Export Your CV</div>', unsafe_allow_html=True)
    
    validation_errors = _validate_cv()
    
    if validation_errors:
        for err in validation_errors:
            st.warning(f"⚠️ {err}")
        st.info("Complete the mandatory fields to enable export.")
    else:
        cv_text = _build_cv_text()
        cv_json = _build_cv_json()
        cv_pdf  = _build_cv_pdf()
        
        btn_col1, btn_col2, btn_col3, prev_col = st.columns([1, 1, 1, 2])
        with btn_col1:
            st.download_button("📄 Download PDF", data=cv_pdf, file_name="my_cv.pdf", mime="application/pdf", use_container_width=True)
        with btn_col2:
            st.download_button("🗒️ Download TXT", data=cv_text, file_name="my_cv.txt", mime="text/plain", use_container_width=True)
        with btn_col3:
            st.download_button("📦 Download JSON", data=cv_json, file_name="my_cv.json", mime="application/json", use_container_width=True)
        
        with prev_col:
            with st.expander("👀 Preview CV (Plain Text)"):
                st.text_area("prev", value=cv_text, height=300, label_visibility="collapsed", disabled=True)
