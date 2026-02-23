#!/usr/bin/env python3
"""Quick serial monitor - prints raw bytes from the controller in hex and ASCII."""
import serial
import time

PORT = '/dev/ttyS0'
BAUD = 115200

print(f"Listening on {PORT} at {BAUD} baud... Press Ctrl+C to stop.")
print("Press buttons on the controller and watch for output.\n")

try:
    with serial.Serial(PORT, BAUD, timeout=1) as s:
        while True:
            data = s.read(s.in_waiting or 1)
            if data:
                hex_str = ' '.join(f'{b:02X}' for b in data)
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
                print(f"HEX: {hex_str:<30} ASCII: {ascii_str}")
except KeyboardInterrupt:
    print("\nDone.")
except serial.SerialException as e:
    print(f"Error: {e}")
