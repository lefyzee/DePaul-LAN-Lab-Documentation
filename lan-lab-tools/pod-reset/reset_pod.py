import telnetlib
import time
import os
from datetime import datetime

# ============================
# LAN Lab Reset Tool Config
# ============================

TERMINAL_SERVER_IP = "192.168.100.1"

START_PORT= 2100
END_PORT = 3600
PORT_STEP= 100

TIMEOUT= 5

LOG_DIR = "logs"


# ============================
# Logging
# ============================

def get_timestamp():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def create_log_file():
        os.makedirs(LOG_DIR, exist_ok=True)
        filename = datetime.now().strftime("reset_%Y-%m-%d_%H-%M-%S.txt")
        return os.path.join(LOG_DIR, filename)

def log(message, log_file):
    entry = f"[{get_timestamp()}] {message}"
    print(entry)

    with open(log_file, "a", encoding="utf-8") as file:
        file.write(entry + "\n")


# =========================
# Device Classification
# =========================

def get_device_type(port):
    if 2100 <= port <= 2700:
        return "router"
    elif 2800 <= port <= 3000:
        return "switch"
    elif 3100 <= port <= 3400:
        return "asa"
    else:
        return "extra"
    

# =========================
# Telnet Helpers
# =========================

def read_output(connection, wait_time=1):
    time.sleep(wait_time)
    return connection.read_very_eager().decode("utf-8", errors="ignore")


def send_command(connection, command, log_file, port):
    log(f"[Port {port}] Sending command: {command}", log_file)
    connection.write(command.encode("ascii") + b"\n")
    time.sleep(1)
    return read_output(connection)


def detect_blocked_access(output):
    blocked_keywords = [
        "password",
        "username",
        "login",
        "authentication failed",
        "access denied"
    ]

    output_lower = output.lower()

    for keyword in blocked_keywords:
        if keyword in output_lower:
            return True

    return False


def detect_console_prompt(output):
    prompt_indicators = [
        ">",
        "#",
        "ciscoasa",
        "router",
        "switch"
    ]

    output_lower = output.lower()

    for indicator in prompt_indicators:
        if indicator in output_lower:
            return True

    return False