#!/usr/bin/env python3
"""
ADB daemon for SNES controller.
Reads keycode names from a FIFO written by snes_read (C program)
and forwards them to the Android TV via adb-shell (pure Python, no binary needed).

FIFO: /tmp/snes_adb
TV:   10.0.0.169:5555
"""
import os
import sys
import time

from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.sign_pythonrsa import PythonRSASigner

FIFO_PATH = "/tmp/snes_adb"
TV_IP = os.environ.get("ADB_TV_IP", "10.0.0.169")
TV_PORT = int(os.environ.get("ADB_TV_PORT", "5555"))
ADB_KEY = os.path.expanduser("~/.android/adbkey")

def connect(signer):
    device = AdbDeviceTcp(TV_IP, TV_PORT, default_transport_timeout_s=9)
    device.connect(rsa_keys=[signer], auth_timeout_s=10)
    print(f"Connected to {TV_IP}:{TV_PORT}", flush=True)
    return device

def main():
    # Create FIFO if needed
    if not os.path.exists(FIFO_PATH):
        os.mkfifo(FIFO_PATH)
        print(f"Created FIFO at {FIFO_PATH}", flush=True)

    signer = PythonRSASigner.FromRSAKeyPath(ADB_KEY)

    device = None
    while device is None:
        try:
            device = connect(signer)
        except Exception as e:
            print(f"ADB connect failed: {e} — retrying in 5s", flush=True)
            time.sleep(5)

    print("Waiting for button events...", flush=True)

    while True:
        try:
            with open(FIFO_PATH, "r") as fifo:
                for line in fifo:
                    keycode = line.strip()
                    if not keycode:
                        continue
                    print(f"→ {keycode}", flush=True)
                    try:
                        device.shell(f"input keyevent {keycode}")
                    except Exception as e:
                        print(f"Send failed: {e} — reconnecting", flush=True)
                        device = None
                        while device is None:
                            try:
                                device = connect(signer)
                            except Exception as e2:
                                print(f"Reconnect failed: {e2} — retrying in 5s", flush=True)
                                time.sleep(5)
                        # Retry the keyevent after reconnect
                        try:
                            device.shell(f"input keyevent {keycode}")
                        except Exception:
                            pass
        except Exception as e:
            print(f"FIFO error: {e}", flush=True)
            time.sleep(1)

if __name__ == "__main__":
    main()
