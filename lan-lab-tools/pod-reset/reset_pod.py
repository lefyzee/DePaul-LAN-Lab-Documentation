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


# =========================
# Reset Logic
# =========================

def reset_router(connection, log_file, port):
    send_command(connection, "", log_file, port)
    send_command(connection, "enable", log_file, port)
    send_command(connection, "write erase", log_file, port)
    send_command(connection, "", log_file, port)
    send_command(connection, "reload", log_file, port)
    send_command(connection, "", log_file, port)


def reset_switch(connection, log_file, port):
    send_command(connection, "", log_file, port)
    send_command(connection, "enable", log_file, port)
    send_command(connection, "write erase", log_file, port)
    send_command(connection, "", log_file, port)
    send_command(connection, "delete /force flash:vlan.dat", log_file, port)
    send_command(connection, "reload", log_file, port)
    send_command(connection, "", log_file, port)


def reset_asa(connection, log_file, port):
    send_command(connection, "", log_file, port)
    send_command(connection, "enable", log_file, port)
    send_command(connection, "write erase", log_file, port)
    send_command(connection, "reload", log_file, port)
    send_command(connection, "", log_file, port)



def reset_device(port, log_file):
    device_type = get_device_type(port)

    log(f"[Port {port}] Connecting to {device_type.upper()} port...", log_file)

    try:
        connection = telnetlib.Telnet(
            TERMINAL_SERVER_IP,
            port,
            timeout=TIMEOUT
        )

        output = read_output(connection, wait_time=2)

        if not output.strip():
            connection.write(b"\n")
            output = read_output(connection, wait_time=2)

        if detect_blocked_access(output):
            log(f"[Port {port}] Password/login prompt detected. Skipping device.", log_file)
            connection.close()
            return "password_protected"

        if not detect_console_prompt(output):
            log(f"[Port {port}] No usable Cisco prompt detected. Skipping.", log_file)
            connection.close()
            return "no_prompt"

        log(f"[Port {port}] Device detected. Beginning reset process.", log_file)

        if device_type == "router":
            reset_router(connection, log_file, port)

        elif device_type == "switch":
            reset_switch(connection, log_file, port)

        elif device_type == "asa":
            reset_asa(connection, log_file, port)

        else:
            log(f"[Port {port}] Extra port detected. No reset commands sent.", log_file)
            connection.close()
            return "extra_detected"

        log(f"[Port {port}] Reset commands completed.", log_file)

        connection.close()
        return "success"

    except ConnectionRefusedError:
        log(f"[Port {port}] No device detected. Connection refused.", log_file)
        return "no_device"

    except TimeoutError:
        log(f"[Port {port}] No device detected. Connection timed out.", log_file)
        return "no_device"

    except Exception as error:
        log(f"[Port {port}] ERROR: {error}", log_file)
        return "error"


# =========================
# Safety Prompt
# =========================

def safety_prompt():
    print("=" * 60)
    print("LAN LAB CISCO POD RESET TOOL")
    print("=" * 60)
    print()
    print("WARNING:")
    print("This script will attempt to erase startup configurations")
    print("on reachable Cisco routers, switches, and ASAs.")
    print()
    print(f"Terminal Server: {TERMINAL_SERVER_IP}")
    print(f"Port Range: {START_PORT} to {END_PORT}, stepping by {PORT_STEP}")
    print()
    confirm = input("Type RESET to continue: ")

    if confirm != "RESET":
        print("Reset cancelled.")
        exit()
