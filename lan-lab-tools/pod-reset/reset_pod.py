import os
from datetime import datetime

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)


# =========================
# LAN Lab Reset Tool Config
# =========================

TERMINAL_SERVER_IP = "192.168.100.1"

START_PORT = 2100
END_PORT = 3600
PORT_STEP = 100

TIMEOUT = 8
LOG_DIR = "logs"


# =========================
# Logging
# =========================

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


def get_netmiko_type(device_type):
    if device_type in ["router", "switch"]:
        return "cisco_ios_telnet"
    elif device_type == "asa":
        return "cisco_asa_telnet"
    return None


# =========================
# Command Helpers
# =========================

def send_timing_command(connection, command, log_file, port):
    log(f"[Port {port}] Sending command: {command}", log_file)

    output = connection.send_command_timing(
        command,
        strip_prompt=False,
        strip_command=False,
    )

    lower_output = output.lower()

    if "confirm" in lower_output or "proceed" in lower_output:
        log(f"[Port {port}] Confirmation prompt detected. Sending ENTER.", log_file)
        output += connection.send_command_timing(
            "",
            strip_prompt=False,
            strip_command=False,
        )

    if "[yes/no]" in lower_output or "yes/no" in lower_output:
        log(f"[Port {port}] Yes/No prompt detected. Sending yes.", log_file)
        output += connection.send_command_timing(
            "yes",
            strip_prompt=False,
            strip_command=False,
        )

    return output


def reset_router(connection, log_file, port):
    log(f"[Port {port}] Router reset started.", log_file)

    send_timing_command(connection, "write erase", log_file, port)
    send_timing_command(connection, "reload", log_file, port)

    log(f"[Port {port}] Router reset commands sent.", log_file)


def reset_switch(connection, log_file, port):
    log(f"[Port {port}] Switch reset started.", log_file)

    send_timing_command(connection, "write erase", log_file, port)
    send_timing_command(connection, "delete /force flash:vlan.dat", log_file, port)
    send_timing_command(connection, "reload", log_file, port)

    log(f"[Port {port}] Switch reset commands sent.", log_file)


def reset_asa(connection, log_file, port):
    log(f"[Port {port}] ASA reset started.", log_file)

    send_timing_command(connection, "write erase", log_file, port)
    send_timing_command(connection, "reload", log_file, port)

    log(f"[Port {port}] ASA reset commands sent.", log_file)


# =========================
# Reset Logic
# =========================

def reset_device(port, log_file):
    device_type = get_device_type(port)

    log(f"[Port {port}] Starting connection attempt.", log_file)

    if device_type == "extra":
        log(f"[Port {port}] Extra port. Checking for connection only.", log_file)

    netmiko_type = get_netmiko_type(device_type)

    if netmiko_type is None:
        log(f"[Port {port}] No reset role assigned. Skipping reset.", log_file)
        return "extra_detected"

    device = {
        "device_type": netmiko_type,
        "host": TERMINAL_SERVER_IP,
        "port": port,
        "username": "",
        "password": "",
        "secret": "",
        "timeout": TIMEOUT,
        "banner_timeout": TIMEOUT,
        "auth_timeout": TIMEOUT,
        "conn_timeout": TIMEOUT,
    }

    try:
        connection = ConnectHandler(**device)

        log(f"[Port {port}] Connected successfully as {device_type.upper()}.", log_file)

        prompt = connection.find_prompt()
        log(f"[Port {port}] Prompt detected: {prompt}", log_file)

        if device_type == "router":
            reset_router(connection, log_file, port)

        elif device_type == "switch":
            reset_switch(connection, log_file, port)

        elif device_type == "asa":
            reset_asa(connection, log_file, port)

        connection.disconnect()

        log(f"[Port {port}] Reset process completed.", log_file)
        return "success"

    except NetmikoAuthenticationException:
        log(f"[Port {port}] Password/login prompt detected. Skipping.", log_file)
        return "password_protected"

    except NetmikoTimeoutException:
        log(f"[Port {port}] No device detected or connection timed out.", log_file)
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
    print(f"Ports: {START_PORT} to {END_PORT}, stepping by {PORT_STEP}")
    print()
    print("Port Mapping:")
    print("2100-2700 = Routers")
    print("2800-3000 = Switches")
    print("3100-3400 = ASAs")
    print("3500-3600 = Extra / future expansion")
    print()

    confirm = input("Type RESET to continue: ")

    if confirm != "RESET":
        print("Reset cancelled.")
        exit()


# =========================
# Main Program
# =========================

def main():
    safety_prompt()

    log_file = create_log_file()

    summary = {
        "success": 0,
        "password_protected": 0,
        "no_device": 0,
        "extra_detected": 0,
        "error": 0,
    }

    log("=" * 60, log_file)
    log("LAN Lab reset started.", log_file)
    log(f"Terminal Server: {TERMINAL_SERVER_IP}", log_file)
    log(f"Scanning ports {START_PORT}-{END_PORT} by {PORT_STEP}", log_file)
    log("=" * 60, log_file)

    for port in range(START_PORT, END_PORT + 1, PORT_STEP):
        result = reset_device(port, log_file)

        if result in summary:
            summary[result] += 1
        else:
            summary["error"] += 1

        log("-" * 60, log_file)

    log("=" * 60, log_file)
    log("LAN Lab reset completed.", log_file)
    log("SUMMARY", log_file)
    log(f"Successful resets: {summary['success']}", log_file)
    log(f"Password protected/skipped: {summary['password_protected']}", log_file)
    log(f"No device detected: {summary['no_device']}", log_file)
    log(f"Extra ports skipped: {summary['extra_detected']}", log_file)
    log(f"Errors: {summary['error']}", log_file)
    log("=" * 60, log_file)

    print()
    print(f"Log saved to: {log_file}")


if __name__ == "__main__":
    main()