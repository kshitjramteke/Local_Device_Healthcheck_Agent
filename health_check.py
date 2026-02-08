import os
import logging
import psutil
import socket
from dotenv import load_dotenv

# ---------------------------
# Setup
# ---------------------------
load_dotenv()

logging.basicConfig(
    filename="remote_health_agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------------------------
# Local Health Check
# ---------------------------
def run_local_health_check():
    """Collects CPU, memory, disk usage."""
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        results = {
            "CPU Usage": cpu,
            "Memory Usage": mem.percent,
            "Disk Usage": disk.percent
        }
        logging.info(f"Local Health Check Results: {results}")
        return results
    except Exception as e:
        logging.error(f"Local Health Check Failed: {str(e)}")
        return {"Error": str(e)}

# ---------------------------
# Network Connectivity
# ---------------------------
def get_network_status():
    """Detects Wi-Fi vs Ethernet and signal quality."""
    try:
        stats = psutil.net_if_stats()
        results = {}
        for iface, stat in stats.items():
            if stat.isup:
                conn_type = "Wi-Fi" if "Wi-Fi" in iface or "Wireless" in iface else "Ethernet"
                speed = stat.speed  # Mbps
                if speed >= 100:
                    quality = "Strong"
                elif speed >= 20:
                    quality = "Moderate"
                else:
                    quality = "Poor"
                results[iface] = {"Type": conn_type, "Speed": speed, "Quality": quality}
        return results
    except Exception as e:
        return {"Error": str(e)}
