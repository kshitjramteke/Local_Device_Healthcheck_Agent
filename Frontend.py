import os
import logging
import streamlit as st
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv
from remote_agent import run_local_health_check  # Import backend function

# ---------------------------
# Setup
# ---------------------------

load_dotenv()

logging.basicConfig(
    filename="streamlit_health_agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

api_key = os.getenv("GEMINI_API_KEY")

# ---------------------------
# Helper: Color-coded status
# ---------------------------

def status_color(value, thresholds):
    if value >= thresholds[1]:
        return f"🔴 {value}%"
    elif value >= thresholds[0]:
        return f"🟠 {value}%"
    else:
        return f"🟢 {value}%"

def overall_status(cpu, mem, disk):
    if cpu >= 85 or mem >= 85 or disk >= 90:
        return "🔴 Critical Issues Detected"
    elif cpu >= 70 or mem >= 70 or disk >= 80:
        return "🟠 System Under Stress"
    else:
        return "🟢 System Healthy"

# ---------------------------
# Streamlit UI
# ---------------------------

st.set_page_config(page_title="System Health Agent", page_icon="🖥️", layout="wide")

# Centered heading and tagline
st.markdown("<h1 style='text-align: center;'>🖥️ System Health Agent</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Monitor CPU, memory, and disk usage with AI guidance</h3>", unsafe_allow_html=True)

# ---------------------------
# Gemini Setup
# ---------------------------

if not api_key:
    st.error("❌ Gemini API key not found. Please set GEMINI_API_KEY in your .env file.")
else:
    client = genai.Client(api_key=api_key)

    PROMPT_TEMPLATE = """
    You are a System Health Agent with diagnostic expertise.
    Capabilities:
    - Run local health checks (CPU, memory, disk).
    - Interpret results and suggest optimizations.
    - Provide troubleshooting steps in clear, actionable language.
    - Offer preventive maintenance tips (e.g., cleaning disk, managing startup apps).
    - Always respond in a structured format with headings and bullet points.
    User query: {query}
    """

    # ---------------------------
    # Tabs for Dashboard & Chat
    # ---------------------------

    tab1, tab2 = st.tabs(["📊 Health Dashboard", "💬 Chat with Agent"])

    # ---------------------------
    # Health Dashboard
    # ---------------------------
    with tab1:
        st.header("🔍 Run Health Check")
        if st.button("Run Health Check"):
            results = run_local_health_check()
            if "Error" in results:
                st.error(results["Error"])
            else:
                # Overall system status
                st.subheader("📌 Overall System Status")
                st.info(overall_status(results['CPU Usage'], results['Memory Usage'], results['Disk Usage']))

                st.success("✅ Health check completed successfully.")
                col1, col2, col3 = st.columns(3)
                col1.metric("CPU Usage", status_color(results['CPU Usage'], (70, 85)))
                col2.metric("Memory Usage", status_color(results['Memory Usage'], (70, 85)))
                col3.metric("Disk Usage", status_color(results['Disk Usage'], (80, 90)))

    # ---------------------------
    # Chat Section
    # ---------------------------
    with tab2:
        st.header("💬 Chat with Health Agent")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        query = st.text_input("Ask me anything about your system health:")

        if query:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=PROMPT_TEMPLATE.format(query=query)
            )
            st.session_state.chat_history.append(("You", query))
            st.session_state.chat_history.append(("Agent", response.text))

        for sender, message in st.session_state.chat_history:
            if sender == "You":
                st.markdown(f"**👤 {sender}:** {message}")
            else:
                st.markdown(f"**🤖 {sender}:** {message}")
