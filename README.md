# Local Device Health Check Dashboard

A Streamlit-based application to monitor **CPU, Memory, Disk, and Network** health on a local device with **AI‑generated fixes**, **real‑time sampling**, **exports**, and a **chat‑based health agent**.

This dashboard is designed for **enterprise use cases**, internal diagnostics, demos, and PoCs.

---

## ✨ Key Features

### ✅ System Health Monitoring
- CPU usage
- Memory usage
- Disk usage
- Overall system health status (Healthy / Under Stress / Critical)

### 🌐 Network Visibility
- Device name (hostname)
- Network interface name
- Adapter description
- Connection type (Wi‑Fi / Ethernet)
- Link speed & quality
- MAC address
- Port/Index (Windows ifIndex)
- Wi‑Fi SSID & signal strength (Windows)

### 🤖 AI‑Generated Fixes (Gemini)
- Root‑cause analysis based on live metrics
- Immediate, **safe** actions
- Preventive best practices
- Non‑destructive, enterprise‑friendly guidance

### 💬 Chat with Health Agent
- Ask questions about system health
- AI-powered responses
- Input auto‑clears after sending

### 📈 Live & Interactive
- Real‑time CPU & Memory sampling
- Auto‑refresh support
- Interactive charts (Altair)

### 📤 Export & Reporting
- Excel export (system snapshot + network info)
- PDF summary report
- CSV fallback if Excel/PDF not available

### 🛰 Optional SNMP Switch Port Lookup
- Map client MAC ➜ switch port (ifIndex / interface)
- Uses BRIDGE‑MIB & IF‑MIB
- Requires SNMP access & permissions

---

## 🗂 Project Structure
Updated Health Check Agent/
├─ backend/
│  ├─ init.py
│  └─ health_check.py          # System & base network checks
├─ frontend/
│  ├─ assets/
│  │  └─ logo.png              # Optional logo
│  └─ frontend.py              # Streamlit dashboard
├─ venv/                       # Virtual environment (local)
├─ requirements.txt
└─ README.md


> ⚠️ Always run Streamlit from the **project root** so the `backend` package is resolved correctly.

---

## 🔧 Prerequisites

- Python **3.10 – 3.12**
- pip
- Virtual environment (recommended)

---

## 🚀 Installation & Setup

### 1️⃣ Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\activate

2️⃣ Install Dependencies

pip install --upgrade pip
pip install -r requirements.txt

3️⃣ Configure Environment Variables
Create a .env file in the project root:

GEMINI_API_KEY=your_google_gemini_api_key_here

Without this key, AI‑generated fixes and chat will be disabled.

4️⃣ (Optional) Add Logo
Place your logo file at:
frontend/assets/cognizant_logo.png

If not present, the dashboard will show a text fallback.

5️⃣ Run the Application
From the project root:
Shellstreamlit run frontend/frontend.pyShow more lines

🖥 How to Use the Dashboard
📊 Health Dashboard Tab

Click Run Health Check to collect metrics
View CPU, Memory, Disk usage with status indicators
Inspect detailed network connectivity
Start real‑time sampling
Enable auto‑refresh
Export results (Excel / PDF)


💬 Chat with Agent Tab

Ask questions like:

Why is my CPU usage high?
How can I improve system performance?


Chat input clears automatically after sending


🛠 Post Health‑Check Fixes & Recommendations
Includes:

Rule‑based fixes (deterministic, safe)
AI‑generated fixes (context‑aware)
Regenerate recommendations anytime


🛰 SNMP Switch Port Lookup (Optional)

Enable from sidebar
Provide:

Switch IP
SNMP read‑only community


Attempts to map:
Client MAC → Bridge Port → ifIndex → Interface Name




🔐 Requires network access and SNMP permissions.
Physical port discovery is not possible without querying the switch.


📦 Requirements
See requirements.txt.
Main dependencies:

streamlit
psutil
pandas
altair
python‑dotenv
google‑genai
openpyxl
reportlab (PDF export)
pysnmp (SNMP lookup)


🧪 Troubleshooting
❌ ModuleNotFoundError: No module named 'backend'
✅ Run Streamlit from the project root:
Shellstreamlit run frontend/frontend.pyShow more lines

❌ AI Fixes Not Working

Check .env file
Ensure GEMINI_API_KEY is valid
Verify outbound internet access


❌ Excel / PDF Export Issues

Ensure openpyxl and reportlab are installed
CSV fallback is provided automatically


❌ SNMP Mapping Not Found

SNMP may be blocked or disabled
Client MAC may not exist in switch FDB
Some corporate networks restrict this feature


🔐 Security & Privacy

Metrics collected locally via psutil
No personal files accessed
AI requests send only numeric metrics & brief summaries
SNMP access is read‑only and optional


🧠 AI Safety Notes

AI recommendations are advisory only
No commands are executed
No destructive actions suggested
Suitable for corporate laptops & endpoints


🧩 Extensibility Ideas

Store metrics in SQLite for 7‑day trends
Add alerts for threshold breaches
Email PDF reports
Add GPU / disk I/O monitoring

Integrate with ITSM tools

