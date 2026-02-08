import os
import logging
import psutil
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
# Local Health Check Function
# ---------------------------

def run_local_health_check():
    """
    Collects basic system health metrics: CPU, memory, disk.
    Returns a dictionary of results.
    """
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
