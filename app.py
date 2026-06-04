import streamlit as st
import os
import re
import json
from dotenv import load_dotenv
from agent import generate_company_report, generate_competitor_snapshot
from pdf_generator import create_pdf

# ── Environment ───────────────────────────────────────────────────────────────
load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Enterprise AI Intelligence Agent",
    page_icon="🧠",
    layout="wide",
)

# ── Session state ─────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "competitor_cache" not in st.session_state:
    st.session_state.competitor_cache = {}   # company_name -> snapshot text


def clear_history():
    st.session_state.history = []
    st.session_state.competitor_cache = {}


# ── Known section titles (must match what agent.py prompts for) ───────────────
KNOWN_SECTIONS = [
    "Company Overview",
    "Key Business Information",
    "Business Challenges",
    "Company-Specific AI Opportunities",
    "Personalized CEO Pitch",
]

TAB_ICONS = {
    "Company Overview": "🏢",
    "Key Business Information": "📊",
    "Business Challenges": "⚠️",
    "Company-Specific AI Opportunities": "🤖",
    "Personalized CEO Pitch": "🎯",
    "Competitor Snapshot": "🔍",
}


# ── Robust section parser ─────────────────────────────────────────────────────
def parse_sections(report_text: str) -> dict:
    """
    Extracts exactly the 5 known sections from the report.

    Strategy:
    1. Build a regex that finds each known H1 header.
    2. For each section, content = text between this header and the next H1.
    3. Any text before the first known H1 is discarded (fixes the ghost-tab bug).
    """
    # Normalise line endings
    text = report_text.replace("\r\n", "\n").replace("\r", "\n")

    # Build a pattern that matches any of the known section headers as H1
    # e.g.  # Company Overview  (with optional trailing spaces / bold markers)
    escaped = [re.escape(s) for s in KNOWN_SECTIONS]
    header_pattern = re.compile(
        r"^#{1,2}\s+(?:\*{1,2})?(" + "|".join(escaped) + r")(?:\*{1,2})?\s*$",
        re.MULTILINE | re.IGNORECASE,
    )

    matches = list(header_pattern.finditer(text))

    if not matches:
        # Fallback: return the whole text under a single key so nothing is lost
        return {"Full Report": text.strip()}

    sections = {}
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        # Normalise title to the canonical casing
        canonical = next(
            (s for s in KNOWN_SECTIONS if s.lower() == title.lower()), title
        )
        content_start = match.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[content_start:content_end].strip()
        sections[canonical] = content

    return sections


# ── JSON export helper ────────────────────────────────────────────────────────
def report_to_json(company_name: str, sections: dict) -> str:
    data = {
        "company": company_name,
        "sections": {},
    }
    for title, content in sections.items():
        # Convert markdown bullets to a plain list for cleaner JSON
        lines = content.split("\n")
        data["sections"][title] = {
            "raw_markdown": content,
            "line_count": len([l for l in lines if l.strip()]),
        }
    return json.dumps(data, indent=2, ensure_ascii=False)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🧠 Agent Controls")
    st.button("🗑️ Clear History", on_click=clear_history, type="secondary")

    st.divider()
    st.subheader("📋 Assessment History")
    if not st.session_state.history:
        st.caption("No assessments generated yet.")
    else:
        for i, item in enumerate(reversed(st.session_state.history)):
            idx = len(st.session_state.history) - i
            st.markdown(f"**{idx}.** {item['company']}")

    st.divider()
    st.caption("Powered by Gemini 2.5 Pro · Google Search · ReportLab")


# ── Main title ────────────────────────────────────────────────────────────────
st.title("🧠 Enterprise AI Intelligence Agent")
st.markdown(
    "Generate deep, factual company intelligence assessments with **Gemini 2.5 Pro** and live web search."
)

# ── Input form ────────────────────────────────────────────────────────────────
with st.form(key="company_input_form"):
    col1, col2 = st.columns([3, 1])
    with col1:
        company_name = st.text_input(
            "Enter Company Name:",
            placeholder="e.g., Adani Realty, NVIDIA, Prestige Group …",
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        submit_button = st.form_submit_button(
            label="⚡ Generate Assessment", type="primary", use_container_width=True
        )

# ── Generate report ───────────────────────────────────────────────────────────
if submit_button and company_name.strip():
    with st.spinner(
        f"Researching **{company_name}** — fetching live data, analyzing challenges, drafting AI opportunities …"
    ):
        try:
            report_content = generate_company_report(company_name.strip())
            st.session_state.history.append(
                {"company": company_name.strip(), "report": report_content}
            )
            # Clear any cached competitor snapshot for this company (fresh run)
            st.session_state.competitor_cache.pop(company_name.strip(), None)
        except Exception as e:
            error_msg = str(e)
            if "RESOURCE_EXHAUSTED" in error_msg:
                st.error(
                    "**Quota exceeded.**\n\n"
                    "- Free tier quota may be exhausted\n"
                    "- Try again in a few minutes\n"
                    "- Or enable billing on your Google AI project"
                )
            else:
                st.error(f"Generation failed:\n\n{error_msg}")

elif submit_button and not company_name.strip():
    st.warning("Please enter a company name.")

# ── Display results ───────────────────────────────────────────────────────────
if st.session_state.history:
    latest = st.session_state.history[-1]
    latest_company = latest["company"]
    latest_report = latest["report"]

    st.divider()
    st.header(f"📄 Intelligence Report: {latest_company}")

    # Parse into clean sections
    sections = parse_sections(latest_report)

    # ── Build tab list: 5 report sections + Competitor Snapshot ──────────────
    tab_titles = []
    for section in KNOWN_SECTIONS:
        if section in sections:
            icon = TAB_ICONS.get(section, "")
            tab_titles.append(f"{icon} {section}")

    # Add competitor tab
    tab_titles.append(f"{TAB_ICONS['Competitor Snapshot']} Competitor Snapshot")

    st_tabs = st.tabs(tab_titles)

    # Render the 5 report sections
    rendered_count = 0
    for section in KNOWN_SECTIONS:
        if section not in sections:
            continue
        icon = TAB_ICONS.get(section, "")
        tab_label = f"{icon} {section}"
        tab_idx = tab_titles.index(tab_label)

        with st_tabs[tab_idx]:
            content = sections[section]

            # Special card-style rendering for CEO Pitch
            if section == "Personalized CEO Pitch":
                st.markdown(
                    """
                    <div style="
                        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                        border-left: 4px solid #e94560;
                        border-radius: 8px;
                        padding: 24px 28px;
                        color: #eaeaea;
                        font-family: Georgia, serif;
                        line-height: 1.75;
                    ">
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(content)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(content)

        rendered_count += 1

    # ── Competitor Snapshot tab ───────────────────────────────────────────────
    competitor_tab_idx = tab_titles.index(
        f"{TAB_ICONS['Competitor Snapshot']} Competitor Snapshot"
    )
    with st_tabs[competitor_tab_idx]:
        st.markdown(
            "Compare **{}** against its top competitors. "
            "Click the button to generate a live snapshot.".format(latest_company)
        )

        already_generated = latest_company in st.session_state.competitor_cache

        if not already_generated:
            if st.button("🔍 Generate Competitor Snapshot", type="primary"):
                with st.spinner("Researching competitors with live web search …"):
                    try:
                        snapshot = generate_competitor_snapshot(latest_company)
                        st.session_state.competitor_cache[latest_company] = snapshot
                        st.rerun()
                    except Exception as e:
                        st.error(f"Competitor snapshot failed: {e}")
        else:
            snapshot_text = st.session_state.competitor_cache[latest_company]
            st.markdown(snapshot_text)
            if st.button("🔄 Refresh Snapshot"):
                st.session_state.competitor_cache.pop(latest_company, None)
                st.rerun()

    # ── Export section ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📥 Export Assessment")

    filename_base = (
        latest_company.replace(" ", "_").replace("/", "_").lower()
    )

    col1, col2, col3, _ = st.columns([1, 1, 1, 3])

    with col1:
        st.download_button(
            label="📝 Markdown (.md)",
            data=latest_report,
            file_name=f"{filename_base}_assessment.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col2:
        try:
            pdf_bytes = create_pdf(latest_report, company_name=latest_company)
            st.download_button(
                label="📄 PDF (.pdf)",
                data=pdf_bytes,
                file_name=f"{filename_base}_assessment.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF error: {e}")

    with col3:
        json_data = report_to_json(latest_company, sections)
        st.download_button(
            label="🗂️ JSON (.json)",
            data=json_data,
            file_name=f"{filename_base}_assessment.json",
            mime="application/json",
            use_container_width=True,
        )