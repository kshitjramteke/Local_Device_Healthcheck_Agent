# -------------------------------------------
# Cognizant Local Device Health Check Dashboard
# Frontend (Streamlit) - Extended with AI Fixes
# -------------------------------------------

# --- Ensure sibling package imports work even if run from inside 'frontend' ---
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import platform
import socket
import json
import re
import subprocess
import time
from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd
import altair as alt
from dotenv import load_dotenv

# App imports
from backend.health_check import run_local_health_check, get_network_status

# =========================
# Setup
# =========================
load_dotenv()

st.set_page_config(
    page_title="Cognizant Local Device Health Check Dashboard",
    page_icon="🖥️",
    layout="wide"
)

logging.basicConfig(
    filename="streamlit_health_agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Theme colors
PRIMARY = "#003366"
ACCENT   = "#0e86d4"
SUCCESS  = "#1b9e77"
WARN     = "#fdae61"
DANGER   = "#d73027"
MUTED    = "#6b7b8c"

st.markdown(
    f"""
    <style>
      .app-title {{
        color: {PRIMARY};
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 0;
      }}
      .app-subtitle {{
        color: {MUTED};
        font-size: 15px;
        margin-top: 2px;
      }}
      .chip {{
        display:inline-block; padding:2px 8px; border-radius:999px;
        background:#eef6ff; color:{PRIMARY}; font-size:12px; border:1px solid #d6e9ff;
      }}
      .metric-box {{
        border:1px solid #edf1f5; border-radius:10px; padding:12px; background:#fafcfe;
      }}
      .section-card {{
        border:1px solid #edf1f5; border-radius:12px; padding:16px; background:white;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# Header with Logo + Title
# =========================
col_logo, col_title, col_time = st.columns([1, 4, 1], vertical_alignment="center")

with col_logo:
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "cognizant_logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, caption=None, width=140)
    else:
        st.markdown(f"<div class='chip'>Cognizant</div>", unsafe_allow_html=True)

with col_title:
    st.markdown("<div class='app-title'>Cognizant Local Device Health Check Dashboard</div>", unsafe_allow_html=True)
    st.markdown("<div class='app-subtitle'>Monitor CPU, memory, disk & network with AI guidance</div>", unsafe_allow_html=True)

with col_time:
    st.caption(f"**{datetime.now().strftime('%d %b %Y, %I:%M %p')}**")

st.divider()

# =========================
# Helpers
# =========================
def status_color(value: float, thresholds: tuple[int, int]) -> str:
    """Return value with traffic signal emoji based on thresholds."""
    try:
        value = float(value)
    except Exception:
        value = 0.0
    if value >= thresholds[1]:
        return f"🔴 {value:.1f}%"
    elif value >= thresholds[0]:
        return f"🟠 {value:.1f}%"
    else:
        return f"🟢 {value:.1f}%"

def overall_status(cpu: float, mem: float, disk: float) -> str:
    try:
        if cpu >= 85 or mem >= 85 or disk >= 90:
            return "🔴 Critical Issues Detected"
        elif cpu >= 70 or mem >= 70 or disk >= 80:
            return "🟠 System Under Stress"
        else:
            return "🟢 System Healthy"
    except Exception:
        return "ℹ️ Status Unavailable"

def to_quality(speed_value) -> str:
    """
    Classify link quality by speed.
    Accepts int Mbps (e.g., 100) or strings like '1 Gbps', '100 Mbps'.
    """
    try:
        if speed_value is None:
            return "Unknown"
        if isinstance(speed_value, (int, float)):
            mbps = float(speed_value)
        else:
            s = str(speed_value).lower().strip()
            m = re.search(r"(\d+(\.\d+)?)\s*(g|m)?bps", s)
            if m:
                num = float(m.group(1))
                unit = m.group(3)
                mbps = num * 1000 if unit == 'g' else num
            else:
                nums = re.findall(r"\d+", s)
                mbps = float(nums[0]) if nums else 0.0
        if mbps >= 100:
            return "Strong"
        elif mbps >= 20:
            return "Moderate"
        else:
            return "Poor"
    except Exception:
        return "Unknown"

def get_device_name() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "Unknown"

def get_richer_network_info() -> list[dict]:
    """
    Enrich network info with:
      - Interface name, Type (Wi‑Fi/Ethernet)
      - Speed, MAC
      - Windows ifIndex (as Port/Index), Adapter description
      - Wi‑Fi SSID & Signal% (Windows)
      - Device (hostname)
    Gracefully falls back if system tools are unavailable.
    """
    import psutil
    info = []
    hostname = get_device_name()

    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    up_ifaces = [n for n, s in stats.items() if getattr(s, "isup", False)]

    system = platform.system()
    ps_map = {}
    wifi_info = {}

    if system == "Windows":
        # Try PowerShell Get-NetAdapter for link speed, mac, ifIndex
        try:
            cmd = [
                "powershell", "-NoProfile", "-Command",
                "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
                "Select-Object Name, InterfaceDescription, LinkSpeed, MacAddress, ifIndex | "
                "ConvertTo-Json -Depth 3"
            ]
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            data = json.loads(out) if out and out.strip() else []
            if isinstance(data, dict):
                data = [data]
            ps_map = {d.get("Name", d.get("InterfaceDescription", "")): d for d in data}
        except Exception:
            ps_map = {}

        # Try netsh for Wi‑Fi SSID and Signal
        try:
            out = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], text=True, stderr=subprocess.DEVNULL)
            ssid = re.search(r"^\s*SSID\s*:\s*(.+)$", out, flags=re.MULTILINE)
            signal = re.search(r"^\s*Signal\s*:\s*(\d+)%", out, flags=re.MULTILINE)
            if ssid:
                wifi_info["SSID"] = ssid.group(1).strip()
            if signal:
                wifi_info["Signal%"] = int(signal.group(1))
        except Exception:
            pass

    for iface in up_ifaces:
        s = stats.get(iface)
        # MAC
        mac = None
        for a in addrs.get(iface, []):
            if getattr(a.family, "name", "") == "AF_LINK" or getattr(a, "family", None) == getattr(__import__("psutil"), "AF_LINK", None):
                mac = a.address

        ctype = "Wi‑Fi" if any(t in iface.lower() for t in ["wi-fi", "wifi", "wlan", "wireless"]) else "Ethernet"

        # Merge with PowerShell row if present (Windows)
        ps_row = ps_map.get(iface) or {}
        if not ps_row:
            # sometimes the key is InterfaceDescription
            for k, v in ps_map.items():
                if iface.lower() in str(k).lower():
                    ps_row = v
                    break

        speed = (
            ps_row.get("LinkSpeed")
            if ps_row.get("LinkSpeed")
            else (f"{s.speed} Mbps" if getattr(s, "speed", 0) else None)
        )

        row = {
            "Device": hostname,
            "Interface": iface,
            "Adapter": ps_row.get("InterfaceDescription") or iface,
            "Type": ctype,
            "Speed": speed,
            "Quality": to_quality(speed),
            "MAC": ps_row.get("MacAddress") or mac,
            "Port/Index": ps_row.get("ifIndex") if ps_row else None,
            "SSID": wifi_info.get("SSID") if ctype == "Wi‑Fi" else None,
            "Signal%": wifi_info.get("Signal%") if ctype == "Wi‑Fi" else None,
        }
        info.append(row)

    return info

# ----- Optional SNMP: map MAC -> switch port (ifIndex/Name) -----
def snmp_mac_to_port(switch_ip: str, community: str, mac_address: str) -> dict | None:
    """
    Attempts to map a client MAC to the switch port via BRIDGE/IF MIBs.
    Returns dict {ifIndex, ifName, ifDescr} or None if not found.
    Requires pysnmp; returns None on ImportError or any failure.
    """
    try:
        from pysnmp.hlapi import (
            SnmpEngine, CommunityData, UdpTransportTarget, ContextData,
            ObjectType, ObjectIdentity, nextCmd
        )
    except Exception:
        return None

    def mac_str_to_oid_suffix(mac: str) -> str:
        parts = [int(p, 16) for p in re.split(r"[:-]", mac)]
        return ".".join(str(p) for p in parts)

    try:
        engine = SnmpEngine()
        auth = CommunityData(community, mpModel=0)  # v1
        target = UdpTransportTarget((switch_ip, 161), timeout=1, retries=1)
        ctx = ContextData()

        # 1) Walk FDB to find dot1dBasePort for the MAC
        fdb_oid_prefix = "1.3.6.1.2.1.17.4.3.1.2"
        # 2) dot1dBasePort -> ifIndex
        baseport_ifindex = "1.3.6.1.2.1.17.1.4.1.2"
        # 3) IF-MIB ifDescr / ifName
        ifdescr_prefix = "1.3.6.1.2.1.2.2.1.2"
        ifname_prefix  = "1.3.6.1.2.1.31.1.1.1.1"

        mac_suffix = mac_str_to_oid_suffix(mac_address)
        fdb_port = None
        for (err_ind, err_stat, err_idx, var_binds) in nextCmd(
            engine, auth, target, ctx,
            ObjectType(ObjectIdentity(fdb_oid_prefix)),
            lexicographicMode=False
        ):
            if err_ind or err_stat:
                break
            for oid, val in var_binds:
                oid_str = ".".join([str(x) for x in oid])
                if oid_str.endswith("." + mac_suffix):
                    try:
                        fdb_port = int(val.prettyPrint())
                    except Exception:
                        pass
                    break
            if fdb_port:
                break

        if not fdb_port:
            return None

        # Map baseport -> ifIndex
        ifindex = None
        for (err_ind, err_stat, err_idx, var_binds) in nextCmd(
            engine, auth, target, ctx,
            ObjectType(ObjectIdentity(baseport_ifindex)),
            lexicographicMode=False
        ):
            if err_ind or err_stat:
                break
            for oid, val in var_binds:
                try:
                    base_port = int(str(oid).split(".")[-1])
                    if base_port == fdb_port:
                        ifindex = int(val.prettyPrint())
                        break
                except Exception:
                    pass
            if ifindex:
                break

        if not ifindex:
            return None

        # Get ifName/ifDescr for that ifIndex
        if_name = None
        if_descr = None
        for prefix in (ifname_prefix, ifdescr_prefix):
            for (err_ind, err_stat, err_idx, var_binds) in nextCmd(
                engine, auth, target, ctx,
                ObjectType(ObjectIdentity(prefix)),
                lexicographicMode=False
            ):
                if err_ind or err_stat:
                    break
                for oid, val in var_binds:
                    if str(oid).endswith("." + str(ifindex)):
                        if prefix == ifname_prefix:
                            if_name = val.prettyPrint()
                        else:
                            if_descr = val.prettyPrint()
                if if_name and if_descr:
                    break

        return {"ifIndex": ifindex, "ifName": if_name, "ifDescr": if_descr}
    except Exception:
        return None

# ----- AI Fixes Helper -----
def generate_ai_fixes(cpu, mem, disk, net_summary):
    """
    Generate AI-based fixes using Gemini based on system metrics.
    Returns plain text recommendations (safe & non-destructive).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ AI recommendations unavailable (GEMINI_API_KEY not configured)."

    try:
        import google.genai as genai
        client = genai.Client(api_key=api_key)

        prompt = f"""
        You are an enterprise IT System Health Assistant.

        Analyze the following local system health metrics and provide:
        1. Likely causes
        2. Immediate safe actions
        3. Preventive best practices

        Constraints:
        - Do NOT suggest destructive actions
        - Do NOT suggest command execution
        - Keep recommendations suitable for corporate laptops
        - Use bullet points and clear headings
        - Keep it concise but actionable

        System Metrics:
        - CPU Usage: {cpu}%
        - Memory Usage: {mem}%
        - Disk Usage: {disk}%
        - Network Summary: {net_summary}

        Respond in a professional, concise, and actionable format.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text

    except Exception as e:
        return f"⚠️ AI recommendation service unavailable: {e}"

# =========================
# Sidebar (controls)
# =========================
with st.sidebar:
    st.header("⚙️ Controls")
    st.caption("Run on-demand checks and view advanced details.")

    run_now = st.button("🔍 Run Health Check")
    show_adv = st.toggle("Show advanced network details", value=True)

    st.markdown("---")
    st.subheader("⏱ Auto‑Refresh")
    auto_refresh = st.toggle("Enable auto‑refresh", value=False)
    refresh_interval = st.number_input("Interval (seconds)", min_value=5, max_value=300, value=20, step=5)

    st.markdown("---")
    st.subheader("📡 Live Sampling")
    sample_secs = st.number_input("Duration (seconds)", min_value=5, max_value=300, value=30, step=5)
    start_stream = st.button("▶ Start Live Sampling")

    st.markdown("---")
    st.subheader("🛰 Switch Port Lookup (SNMP)")
    snmp_enabled = st.toggle("Enable SNMP lookup", value=False)
    switch_ip = st.text_input("Switch IP", value="", placeholder="e.g., 10.0.0.1")
    snmp_comm = st.text_input("Community (RO)", value="public", type="password")
    st.caption("Requires network access and SNMP enabled on the switch. Uses BRIDGE/IF MIBs.")

# Initialize session state
if "last_results" not in st.session_state:
    st.session_state.last_results = None
if "chat_msgs" not in st.session_state:
    st.session_state.chat_msgs = []

# =========================
# Tabs
# =========================
tab1, tab2 = st.tabs(["📊 Health Dashboard", "💬 Chat with Agent"])

# -------------------------
# 📊 Dashboard
# -------------------------
with tab1:
    # Run check on click
    if run_now:
        results = run_local_health_check()
        st.session_state.last_results = results

    # Show results (previous or current)
    results = st.session_state.last_results or {"CPU Usage": 0, "Memory Usage": 0, "Disk Usage": 0}

    st.subheader("📌 Overall System Status")
    st.info(overall_status(results.get('CPU Usage', 0), results.get('Memory Usage', 0), results.get('Disk Usage', 0)))

    # Metrics row
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
        st.metric("CPU Usage", status_color(results.get('CPU Usage', 0), (70, 85)))
        st.progress(min(int(results.get('CPU Usage', 0)), 100))
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
        st.metric("Memory Usage", status_color(results.get('Memory Usage', 0), (70, 85)))
        st.progress(min(int(results.get('Memory Usage', 0)), 100))
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
        st.metric("Disk Usage", status_color(results.get('Disk Usage', 0), (80, 90)))
        st.progress(min(int(results.get('Disk Usage', 0)), 100))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")

    # ================== Network connectivity ==================
    st.subheader("🌐 Network Connectivity")

    # Base status from backend (for compatibility with your existing logic)
    try:
        base_net = get_network_status() or {}
    except Exception as e:
        base_net = {"Error": str(e)}

    if "Error" in base_net:
        st.error(base_net["Error"])
    else:
        # Enrich with local Windows details (if available)
        rich = get_richer_network_info()

        # Display cards per interface
        for row in rich:
            with st.container(border=True):
                top_a, top_b, top_c, top_d = st.columns([2.2, 1.2, 1.2, 1.2])
                with top_a:
                    st.markdown(f"**Interface:** {row['Interface']}")
                    st.caption(row["Adapter"])
                with top_b:
                    st.markdown(f"**Type:** {row['Type']}")
                    if row.get("SSID"):
                        st.caption(f"SSID: {row['SSID']}")
                with top_c:
                    st.markdown(f"**Speed:** {row['Speed'] or '—'}")
                    st.caption(f"Quality: {row['Quality']}")
                with top_d:
                    st.markdown(f"**Port/Index:** {row['Port/Index'] or '—'}")
                    st.caption(f"MAC: {row['MAC'] or '—'}")

                bottom_a, bottom_b = st.columns([2, 2])
                with bottom_a:
                    st.markdown(f"**Device:** {row['Device']}")
                with bottom_b:
                    if row.get("Signal%") is not None:
                        st.progress(int(row["Signal%"]))
                        st.caption(f"Wi‑Fi Signal: {row['Signal%']}%")

            if snmp_enabled and switch_ip.strip() and row.get("MAC"):
                with st.expander(f"🛰 SNMP Mapping for {row['Interface']} ({row['MAC']})"):
                    mapping = snmp_mac_to_port(switch_ip.strip(), snmp_comm.strip(), row["MAC"])
                    if mapping:
                        st.success(
                            f"Switch mapping found → ifIndex: **{mapping.get('ifIndex')}**, "
                            f"ifName: **{mapping.get('ifName') or '—'}**, "
                            f"ifDescr: **{mapping.get('ifDescr') or '—'}**"
                        )
                    else:
                        st.info("No SNMP mapping found (or SNMP not available/allowed).")

        if not rich:
            st.info("No active network interfaces detected.")

    st.markdown("")

    # ================== Live Sampling (real-time) ==================
    st.subheader("📈 Real-time Resource Sampling")
    st.caption("Samples CPU & Memory in real-time for the selected duration.")
    if start_stream:
        import psutil
        placeholder = st.empty()
        t0 = time.time()
        series = []
        with st.spinner(f"Sampling for {sample_secs} seconds…"):
            for i in range(int(sample_secs)):
                cpu = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory().percent
                series.append({"Second": i + 1, "CPU": cpu, "Memory": mem})
                df_live = pd.DataFrame(series)
                ch_cpu = alt.Chart(df_live).mark_line(color="crimson").encode(x="Second", y="CPU")
                ch_mem = alt.Chart(df_live).mark_line(color="steelblue").encode(x="Second", y="Memory")
                placeholder.altair_chart(ch_cpu + ch_mem, width="stretch")
        st.success(f"Completed in ~{int(time.time() - t0)}s")

    # ================== Demo Chart (static) ==================
    st.subheader("📊 Snapshot Trend (Demo)")
    demo_data = pd.DataFrame({
        "Time": ["00:00", "01:00", "02:00", "03:00"],
        "CPU": [20, 45, 70, 55],
        "Memory": [30, 50, 65, 60]
    })
    cpu_chart = alt.Chart(demo_data).mark_line(color="red").encode(x="Time", y="CPU")
    mem_chart = alt.Chart(demo_data).mark_line(color="blue").encode(x="Time", y="Memory")
    st.altair_chart(cpu_chart + mem_chart, width="stretch")

    # ================== Export ==================
    st.subheader("📤 Export Current Snapshot")

    snapshot = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "device": get_device_name(),
        "cpu_percent": results.get("CPU Usage", None),
        "memory_percent": results.get("Memory Usage", None),
        "disk_percent": results.get("Disk Usage", None),
        "overall_status": overall_status(results.get('CPU Usage', 0),
                                         results.get('Memory Usage', 0),
                                         results.get('Disk Usage', 0)),
    }
    net_rows = get_richer_network_info()

    # Excel (snapshot + network), fallback to CSV if openpyxl/reportlab missing
    excel_bytes = None
    try:
        from pandas import ExcelWriter
        excel_buf = BytesIO()
        with pd.ExcelWriter(excel_buf, engine="openpyxl") as xw:
            pd.DataFrame([snapshot]).to_excel(xw, sheet_name="Snapshot", index=False)
            df_net = pd.DataFrame(net_rows)
            if not df_net.empty:
                df_net.to_excel(xw, sheet_name="Network", index=False)
        excel_bytes = excel_buf.getvalue()
        st.download_button(
            "⬇️ Download Excel (Snapshot + Network)",
            data=excel_bytes,
            file_name=f"health_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        st.caption(f"Excel export unavailable: {e} — falling back to CSV.")
        csv_bytes = pd.DataFrame([snapshot]).to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV (Snapshot)",
            data=csv_bytes,
            file_name=f"health_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

    # PDF bytes (optional)
    def make_pdf_bytes(snapshot_dict: dict, net_list: list[dict]) -> bytes | None:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm
        except Exception:
            return None

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        x = 2 * cm
        y = h - 2 * cm

        def line(txt, dy=0.6):
            nonlocal y
            c.drawString(x, y, txt)
            y -= dy * cm

        c.setFont("Helvetica-Bold", 14)
        line("Cognizant Local Device Health Check Dashboard", dy=0.9)

        c.setFont("Helvetica", 10)
        line(f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
        line(f"Device: {snapshot_dict.get('device', 'Unknown')}")
        line("")

        c.setFont("Helvetica-Bold", 12)
        line("System Snapshot", dy=0.8)
        c.setFont("Helvetica", 10)
        line(f"Overall Status : {snapshot_dict.get('overall_status')}")
        line(f"CPU Usage      : {snapshot_dict.get('cpu_percent')}%")
        line(f"Memory Usage   : {snapshot_dict.get('memory_percent')}%")
        line(f"Disk Usage     : {snapshot_dict.get('disk_percent')}%")
        line("")

        c.setFont("Helvetica-Bold", 12)
        line("Network Interfaces", dy=0.8)
        c.setFont("Helvetica", 10)
        if net_list:
            for n in net_list:
                line(f"- {n.get('Interface')} | {n.get('Type')} | {n.get('Speed')} | MAC {n.get('MAC')} | Port/Index {n.get('Port/Index')}")
                if n.get("SSID"):
                    line(f"  SSID {n.get('SSID')} / Signal {n.get('Signal%')}%")
        else:
            line("No active interfaces.")

        c.showPage()
        c.save()
        return buf.getvalue()

    pdf_bytes = make_pdf_bytes(snapshot, net_rows)
    if pdf_bytes:
        st.download_button(
            "⬇️ Download PDF Summary",
            data=pdf_bytes,
            file_name=f"health_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
        )
    else:
        st.caption("Install `reportlab` to enable PDF export: `pip install reportlab`")

    # Auto-refresh
    if auto_refresh:
        st.caption(f"Auto-refreshing in {refresh_interval}s…")
        time.sleep(int(refresh_interval))
        try:
            st.rerun()
        except Exception:
            st.experimental_rerun()

# -------------------------
# 💬 Chat with Agent (auto‑clears input)
# -------------------------
with tab2:
    st.subheader("💬 Chat with Health Agent")

    # Gemini client
    import google.genai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("❌ Gemini API key not found. Please set GEMINI_API_KEY in your .env file.")
    else:
        client = genai.Client(api_key=api_key)

        PROMPT_TEMPLATE = """
        You are a System Health Agent with diagnostic expertise.
        Capabilities:
        - Interpret system metrics (CPU, memory, disk, network).
        - Explain why a system may be under stress.
        - Suggest optimizations and preventive maintenance.
        - Respond in structured format with headings and bullet points.
        User query: {query}
        """

        # Render history
        for role, content in st.session_state.chat_msgs:
            with st.chat_message("user" if role == "user" else "assistant"):
                st.markdown(content)

        # Chat input (auto‑clears after submit)
        user_input = st.chat_input("Ask me anything about your system health…")
        if user_input:
            st.session_state.chat_msgs.append(("user", user_input))
            with st.chat_message("user"):
                st.markdown(user_input)

            # Get response
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=PROMPT_TEMPLATE.format(query=user_input)
                )
                reply_text = response.text if hasattr(response, "text") else "I responded, but couldn't parse the reply."
            except Exception as e:
                reply_text = f"Sorry, I couldn't reach the AI service: {e}"

            st.session_state.chat_msgs.append(("assistant", reply_text))
            with st.chat_message("assistant"):
                st.markdown(reply_text)

# =========================
# Actionable Notes (Rule‑Based + AI)
# =========================
st.divider()

with st.expander("🛠️ Post Health‑Check Fixes & Recommendations", expanded=False):

    st.markdown("### ✅ Recommended Actions After Running Health Check")

    # Pull from last_results to ensure availability outside tab1
    current = st.session_state.last_results or {"CPU Usage": 0, "Memory Usage": 0, "Disk Usage": 0}
    cpu = current.get("CPU Usage", 0)
    mem = current.get("Memory Usage", 0)
    disk = current.get("Disk Usage", 0)

    # ---------------- CPU ----------------
    if cpu >= 80:
        st.markdown("#### 🔴 High CPU Usage Detected")
        st.markdown("""
        - Close unused or background applications (Task Manager → Processes).
        - Check for long‑running or stuck processes consuming CPU.
        - Restart applications that are not responding.
        - Ensure antivirus scans are not running repeatedly.
        - Reboot the system if high CPU persists for a long time.
        """)
    else:
        st.markdown("#### 🟢 CPU Status Normal")
        st.markdown("""
        - No immediate CPU‑related action required.
        - Continue monitoring during peak usage hours.
        """)

    # ---------------- Memory ----------------
    if mem >= 80:
        st.markdown("#### 🔴 High Memory Usage Detected")
        st.markdown("""
        - Close unused browser tabs and memory‑heavy applications.
        - Restart applications consuming excessive memory.
        - Disable unnecessary startup programs.
        - Consider upgrading RAM if usage is consistently high.
        """)
    else:
        st.markdown("#### 🟢 Memory Status Normal")
        st.markdown("""
        - Memory utilization is within acceptable limits.
        - No optimization needed at this time.
        """)

    # ---------------- Disk ----------------
    if disk >= 85:
        st.markdown("#### 🔴 High Disk Usage Detected")
        st.markdown("""
        - Delete temporary files (Disk Cleanup / Storage Sense).
        - Clear application cache folders.
        - Remove unused software and old files.
        - Ensure sufficient free space (minimum 15–20% recommended).
        """)
    else:
        st.markdown("#### 🟢 Disk Status Normal")
        st.markdown("""
        - Disk space is healthy.
        - Maintain regular cleanup to avoid future issues.
        """)

    # ---------------- Network ----------------
    st.markdown("#### 🌐 Network Connectivity Recommendations")
    st.markdown("""
    - Prefer **wired (Ethernet)** connections for stability and speed.
    - If on Wi‑Fi:
      - Move closer to the access point.
      - Avoid congested networks.
      - Switch to 5 GHz where available.
    - Disconnect VPN if not required for current work.
    - Restart network adapter if frequent drops are observed.
    """)

    # ---------------- General ----------------
    st.markdown("#### 🧠 General Best Practices")
    st.markdown("""
    - Restart your system periodically to clear stale processes.
    - Keep OS and drivers updated.
    - Avoid running heavy applications simultaneously.
    - Schedule regular health checks to catch issues early.
    """)

    st.markdown("---")
    st.caption(
        "💡 These recommendations are safe, non‑intrusive actions. "
        "For persistent issues, contact IT support or system administrators."
    )

    # ---------------- AI‑Generated Fixes ----------------
    st.markdown("---")
    st.markdown("### 🤖 AI‑Generated Fixes (Based on Current Health Check)")

    # Build a short network summary for AI
    net_info = get_richer_network_info()
    if net_info:
        primary_net = net_info[0]
        net_summary = (
            f"{primary_net.get('Type')} connection, "
            f"Speed: {primary_net.get('Speed')}, "
            f"Quality: {primary_net.get('Quality')}"
        )
    else:
        net_summary = "No active network detected"

    # Let user trigger or regenerate AI suggestions
    if st.button("✨ Generate / Regenerate AI Fixes"):
        with st.spinner("Analyzing system metrics and generating AI recommendations…"):
            ai_fixes = generate_ai_fixes(cpu, mem, disk, net_summary)
        st.markdown(ai_fixes)
    else:
        st.caption("Click above to generate tailored AI recommendations for this snapshot.")