import streamlit as st
import os
import re
from dotenv import load_dotenv
from agent import generate_company_report
from pdf_generator import create_pdf

# Initialize environment variables
load_dotenv()

# Streamlit Page Configuration
st.set_page_config(
    page_title="Enterprise AI Intelligence Agent", page_icon="🧠", layout="wide"
)

# Initialize Session State for Chat History
if "history" not in st.session_state:
    st.session_state.history = []


def clear_history():
    st.session_state.history = []


# Sidebar
with st.sidebar:
    st.header("Agent Controls")
    st.button("Clear History", on_click=clear_history, type="secondary")

    st.divider()
    st.subheader("Assessment History")
    if not st.session_state.history:
        st.write("No assessments generated yet.")
    else:
        for i, item in enumerate(reversed(st.session_state.history)):
            st.markdown(f"**{len(st.session_state.history) - i}. {item['company']}**")

# Main UI
st.title("Enterprise AI Intelligence Agent")
st.markdown(
    "Generate deep, factual company intelligence assessments using Gemini 2.5 Pro."
)

# Input Section
with st.form(key="company_input_form"):
    col1, col2 = st.columns([3, 1])
    with col1:
        company_name = st.text_input(
            "Enter Company Name:", placeholder="e.g., NVIDIA, Stripe, local business..."
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Alignment fix
        submit_button = st.form_submit_button(
            label="Generate Assessment", type="primary", use_container_width=True
        )

# Processing Logic
if submit_button and company_name:
    with st.spinner(
        f"Agent is researching {company_name}, analyzing business data, and formatting the assessment..."
    ):
        try:
            report_content = generate_company_report(company_name)
            st.session_state.history.append(
                {"company": company_name, "report": report_content}
            )
        except Exception as e:

            error_msg = str(e)

            if "RESOURCE_EXHAUSTED" in error_msg:

                st.error("""
                        Quota exceeded.

                        Possible reasons:

                        • Free tier quota exhausted
                        • Billing not enabled
                        • Gemini Pro unavailable for your project

                        Try again later or switch to Gemini Flash.
                        """)

            else:
                st.error(f"Generation failed:\n{error_msg}")

# Display Results
if st.session_state.history:
    latest_company = st.session_state.history[-1]["company"]
    latest_report = st.session_state.history[-1]["report"]

    st.header(f"Intelligence Report: {latest_company}")

    # Parse Markdown into Sections for Tabs based on H1 (# )
    # The regex splits on lines starting with a single hash followed by space.
    raw_sections = re.split(r"^#\s+", latest_report, flags=re.MULTILINE)

    tabs_dict = {}
    for section in raw_sections:
        if not section.strip():
            continue
        lines = section.split("\n", 1)
        title = lines[0].strip()
        content = lines[1].strip() if len(lines) > 1 else ""
        tabs_dict[title] = content

    # Render Tabs
    if tabs_dict:
        # Create tabs dynamically based on extracted headers
        st_tabs = st.tabs(list(tabs_dict.keys()))
        for idx, (title, content) in enumerate(tabs_dict.items()):
            with st_tabs[idx]:
                st.markdown(content)
    else:
        # Fallback if markdown formatting slightly deviates
        st.markdown(latest_report)

    st.divider()

    # Export Section
    st.subheader("Export Assessment")
    col_export_1, col_export_2, _ = st.columns([1, 1, 4])

    filename_base = latest_company.replace(" ", "_").replace("/", "_").lower()

    with col_export_1:
        st.download_button(
            label="Download Markdown (.md)",
            data=latest_report,
            file_name=f"{filename_base}_assessment.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col_export_2:
        try:
            pdf_bytes = create_pdf(latest_report)
            st.download_button(
                label="Download PDF (.pdf)",
                data=pdf_bytes,
                file_name=f"{filename_base}_assessment.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF Generation Error: {e}")
