from netmiko import ConnectHandler

# Change port number to whatever your serial port is
device = {
    "device_type": "cisco_ios_serial",
    "serial_settings": {
        "port": "COM5",
        "baudrate": 9600,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
    },
    "username": "",
    "password": "",
    "secret": "",
    "timeout": 10,
}

connection = ConnectHandler(**device)

print("Connected successfully.")

prompt = connection.find_prompt()
print(f"Prompt detected: {prompt}")

output = connection.send_command_timing(
    "show version",
    strip_prompt=False,
    strip_command=False
)

print(output)

connection.disconnect()