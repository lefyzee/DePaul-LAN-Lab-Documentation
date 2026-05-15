import telnetlib
import time
import os
from datetime import datetime

# ==============================
# LAN Lab Reset Tool Config
# ==============================

TERMINAL_SERVER_IP = "192.168.100.1"

START_PORT= 2100
END_PORT = 3600
PORT_STEP= 100

TIMEOUT= 5

LOG_DIR = "logs"


# ==============================
# Logging
# ==============================