import os
import sys
from datetime import datetime

# ==============================
# Check if netmiko is installed
# ==============================
try:
    from netmiko import ConnectHandler
    from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
except ModuleNotFoundError:
    print("ERROR: Netmiko is not installed.")
    print("Run: python -m pip install -r requirements.txt")
    sys.exit(1)

# The MRV's IP address
TERMINAL_SERVER_IP = "192.168.100.1"

# Change these ports to either test one device or set it from START_PORT to 2100 to END_PORT 3600 to reset all devices
START_PORT = 2100
END_PORT = 2100
PORT_STEP = 100

# Send the commands to the logs folder
TIMEOUT = 10
LOG_DIR = "logs"

# Check the time
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


def get_device_type(port):
    if 2100 <= port <= 2700:
        return "router"
    elif 2800 <= port <= 3000:
        return "switch"
    elif 3100 <= port <= 3400:
        return "asa"
    return "extra"


def get_netmiko_type(device_type):
    if device_type in ["router", "switch"]:
        return "cisco_ios_telnet"
    if device_type == "asa":
        return "cisco_asa_telnet"
    return None


def send_command(connection, command, log_file, port):
    display = command if command else "[ENTER]"
    log(f"[Port {port}] Sending command: {display}", log_file)

    output = connection.send_command_timing(
        command,
        strip_prompt=False,
        strip_command=False,
        delay_factor=2,
    )

    log(f"[Port {port}] Output:\n{output}", log_file)
    return output


def handle_reload(connection, log_file, port):
    output = send_command(connection, "reload", log_file, port)
    lower = output.lower()

    if "system configuration has been modified" in lower or "save?" in lower:
        log(f"[Port {port}] Save prompt detected. Sending 'no'.", log_file)
        output = send_command(connection, "no", log_file, port)
        lower = output.lower()

    if "confirm" in lower or "proceed" in lower:
        log(f"[Port {port}] Reload confirmation detected. Sending ENTER.", log_file)
        send_command(connection, "", log_file, port)


def reset_ios_device(connection, log_file, port, is_switch=False):
    try:
        connection.enable()
    except Exception:
        log(f"[Port {port}] Enable mode may already be active.", log_file)

    prompt = connection.find_prompt()
    log(f"[Port {port}] Current prompt: {prompt}", log_file)

    if not prompt.strip().endswith("#"):
        log(f"[Port {port}] Not in privileged EXEC mode. Skipping.", log_file)
        return False

    output = send_command(connection, "write erase", log_file, port)

    if "confirm" in output.lower() or "erase of nvram" in output.lower():
        send_command(connection, "", log_file, port)

    if is_switch:
        send_command(connection, "delete /force flash:vlan.dat", log_file, port)

    handle_reload(connection, log_file, port)
    return True


def reset_asa(connection, log_file, port):
    try:
        connection.enable()
    except Exception:
        log(f"[Port {port}] Enable mode may already be active.", log_file)

    send_command(connection, "write erase", log_file, port)
    handle_reload(connection, log_file, port)
    return True


def reset_device(port, log_file):
    device_type = get_device_type(port)
    netmiko_type = get_netmiko_type(device_type)

    log(f"[Port {port}] Connecting to {device_type.upper()} port.", log_file)

    if netmiko_type is None:
        log(f"[Port {port}] Extra/future port. No reset role assigned.", log_file)
        return "extra_detected"

# ==============
# Main Logic
# ==============

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
        log(f"[Port {port}] Connected successfully.", log_file)

        prompt = connection.find_prompt()
        log(f"[Port {port}] Prompt detected: {prompt}", log_file)

        if device_type == "router":
            success = reset_ios_device(connection, log_file, port)

        elif device_type == "switch":
            success = reset_ios_device(connection, log_file, port, is_switch=True)

        elif device_type == "asa":
            success = reset_asa(connection, log_file, port)

        else:
            success = False

        connection.disconnect()

        if success:
            log(f"[Port {port}] Reset initiated successfully.", log_file)
            return "success"

        return "error"

    except NetmikoAuthenticationException:
        log(f"[Port {port}] Password/login prompt detected. Skipping.", log_file)
        return "password_protected"

    except NetmikoTimeoutException:
        log(f"[Port {port}] No device detected or connection timed out.", log_file)
        return "no_device"

    except Exception as error:
        log(f"[Port {port}] ERROR: {error}", log_file)
        return "error"


def safety_prompt():
    print("=" * 60)
    print("LAN LAB CISCO POD RESET TOOL")
    print("=" * 60)
    print()
    print("WARNING:")
    print("This will erase startup configurations and reload reachable devices.")
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
        sys.exit(0)


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
        summary[result] = summary.get(result, 0) + 1
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