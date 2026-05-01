import streamlit as st
import asyncio
import os
import sys
from dotenv import load_dotenv

# First Principles Fix: Load environment variables into the Streamlit context
load_dotenv()

# Ensure absolute imports resolve correctly for the Streamlit environment
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from src.graph_engine import run_awaas_analysis

# --- UI Configuration ---
st.set_page_config(
    page_title="Awaas AI | Neighborhood Intelligence",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for high-fidelity palette (Warm Ivory, Deep Charcoal, Luxe Antique Gold)
st.markdown("""
    <style>
    .stApp {
        background-color: #FAF9F6;
        color: #2C3034;
    }
    h1, h2, h3, p, span {
        color: #2C3034 !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* Button Styling */
    .stButton>button {
        background-color: #D4AF37;
        color: #2C3034;
        border: none;
        border-radius: 4px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover, .stButton>button:focus, .stButton>button:active {
        background-color: #C5A030 !important;
        color: #2C3034 !important;
        border-color: transparent !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* Input Field Fix: Force Contrast and override focus outlines */
    .stTextInput>div>div>input {
        background-color: #FAF9F6 !important;
        color: #2C3034 !important;
        border: 2px solid #D4AF37 !important;
    }
    .stTextInput>div>div>input:focus {
        box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.5) !important;
    }
    
    /* Alert Styling */
    .stAlert {
        background-color: rgba(212, 175, 55, 0.1);
        border-color: #D4AF37;
        color: #2C3034;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Application Header ---
st.title("Awaas AI")
st.markdown("### Neighborhood Intelligence for Indian Real Estate")
st.markdown("Research any Indian neighborhood in 15 seconds using verified open data + AI synthesis.")
st.markdown("---")

# --- Input Section ---
col1, col2 = st.columns([3, 1])
with col1:
    pincode_input = st.text_input("Enter 6-digit PIN Code", placeholder="e.g., 560034", max_chars=6, label_visibility="collapsed")
with col2:
    analyze_btn = st.button("Generate Report", use_container_width=True)

# --- Execution Logic ---
if analyze_btn:
    if not pincode_input or len(pincode_input) != 6 or not pincode_input.isdigit():
        st.error("Please enter a valid 6-digit Indian PIN code.")
    else:
        async def fetch_report():
            return await run_awaas_analysis(pincode_input, user_criteria={"investment_type": "general buyer"})
        
        with st.spinner('Orchestrating Autonomous Pipeline...'):
            try:
                final_state = asyncio.run(fetch_report())
                
                if final_state.get("report_generated"):
                    st.success("Report generated successfully!")
                    
                    st.markdown(final_state.get("markdown_report", ""))
                    st.markdown("---")
                    
                    pdf_bytes = final_state.get("pdf_bytes")
                    if pdf_bytes:
                        st.download_button(
                            label="Download PDF Report",
                            data=pdf_bytes,
                            file_name=f"Awaas_Report_{pincode_input}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.error("Pipeline failed to generate a report. See risk flags below.")
                    for flag in final_state.get("riskflags", ["Unknown error."]):
                        st.write(f"- {flag}")
                    
            except Exception as e:
                st.error(f"Critical System Failure: {str(e)}")