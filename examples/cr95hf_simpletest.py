# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Basic demo for the CR95HF NFC reader
"""

import board
import busio
import time
from cr95hf import CR95HF

uart = busio.UART(
    board.D32,
    board.D33,
    baudrate=57600,
    bits=8,
    stop=2,
    timeout=0.1
)
nfc = CR95HF(uart)
print(f"CR95HF ready! Device: {nfc.device_name}\n")

while True:
    uid, sak = nfc.read_tag()
    
    if uid:
        print(f"UID: {uid.hex().upper()}")
        print(f"Type: {nfc.card_type(sak)}\n")
    
    time.sleep(0.2)
