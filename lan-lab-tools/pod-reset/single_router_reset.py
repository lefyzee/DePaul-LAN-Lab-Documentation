import os
from datetime import datetime

from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

SERIAL_PORT = "COM5"
TIMEOUT = 10
LOG_DIR = "logs"


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_log_file():
    os.makedirs(LOG_DIR, exist_ok=True)
    filename = datetime.now().strftime("serial_reset_%Y-%m-%d_%H-%M-%S.txt")
    return os.path.join(LOG_DIR, filename)


def log(message, log_file):
    entry = f"[{get_timestamp()}] {message}"
    print(entry)
    with open(log_file, "a", encoding="utf-8") as file:
        file.write(entry + "\n")


def send_command(connection, command, log_file):
    display_command = command if command else "[ENTER]"
    log(f"Sending command: {display_command}", log_file)

    output = connection.send_command_timing(
        command,
        strip_prompt=False,
        strip_command=False,
        delay_factor=2,
    )

    log(f"Output:\n{output}", log_file)
    return output


def reset_router(connection, log_file):
    log("Attempting to enter enable mode.", log_file)

    try:
        connection.enable()
    except Exception:
        log("Enable mode may already be active or no enable password is set.", log_file)

    prompt = connection.find_prompt()
    log(f"Current prompt: {prompt}", log_file)

    if not prompt.strip().endswith("#"):
        log("Not in privileged EXEC mode. Cannot erase config.", log_file)
        return False

    log("Erasing startup configuration.", log_file)

    output = send_command(connection, "write erase", log_file)

    if "confirm" in output.lower() or "erase of nvram" in output.lower():
        send_command(connection, "", log_file)

    log("Sending reload command.", log_file)

    output = send_command(connection, "reload", log_file)
    lower_output = output.lower()

    if "system configuration has been modified" in lower_output or "save?" in lower_output:
        log("Reload asked to save config. Sending 'no'.", log_file)
        output = send_command(connection, "no", log_file)
        lower_output = output.lower()

    if "confirm" in lower_output or "proceed" in lower_output:
        log("Reload confirmation detected. Sending ENTER.", log_file)
        send_command(connection, "", log_file)

    log("Reset commands sent. Router should now reload.", log_file)
    return True


def safety_prompt():
    print("=" * 60)
    print("LAN LAB SINGLE ROUTER SERIAL RESET TEST")
    print("=" * 60)
    print()
    print("WARNING:")
    print("This will erase the startup configuration on the router connected to COM5.")
    print("The router will reload after the erase command.")
    print()
    confirm = input("Type RESET to continue: ")

    if confirm != "RESET":
        print("Reset cancelled.")
        exit()


def main():
    safety_prompt()
    log_file = create_log_file()

    log("=" * 60, log_file)
    log("Single router serial reset started.", log_file)
    log(f"Serial Port: {SERIAL_PORT}", log_file)
    log("=" * 60, log_file)

    device = {
        "device_type": "cisco_ios_serial",
        "serial_settings": {
            "port": SERIAL_PORT,
            "baudrate": 9600,
            "bytesize": 8,
            "parity": "N",
            "stopbits": 1,
        },
        "username": "",
        "password": "",
        "secret": "",
        "timeout": TIMEOUT,
    }

    try:
        connection = ConnectHandler(**device)
        log("Connected successfully.", log_file)

        prompt = connection.find_prompt()
        log(f"Prompt detected: {prompt}", log_file)

        reset_router(connection, log_file)

        connection.disconnect()

    except NetmikoAuthenticationException:
        log("Password/login prompt detected. Reset failed.", log_file)

    except NetmikoTimeoutException:
        log("Connection timed out. Reset failed.", log_file)

    except Exception as error:
        log(f"ERROR: {error}", log_file)

    log("=" * 60, log_file)
    log("Script completed.", log_file)
    log("=" * 60, log_file)

    print()
    print(f"Log saved to: {log_file}")


if __name__ == "__main__":
    main()