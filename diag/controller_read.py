#!/usr/bin/env python3
"""
SNES controller passive tap using interrupt-driven reads.
The SNES drives Clock and Latch; Pi reads Data on clock edges.

GPIO 17 (Pin 11) = Clock  (INPUT - driven by SNES)
GPIO 27 (Pin 13) = Latch  (INPUT - driven by SNES)
GPIO 22 (Pin 15) = Data   (INPUT - driven by controller)

Requires SNES to be powered on with a game cartridge running.
"""
import RPi.GPIO as GPIO
import time
import threading

CLOCK = 17
LATCH = 27
DATA  = 22

BUTTONS = ['B', 'Y', 'Select', 'Start', 'Up', 'Down', 'Left', 'Right',
           'A', 'X', 'L', 'R']

GPIO.setmode(GPIO.BCM)
GPIO.setup(CLOCK, GPIO.IN)
GPIO.setup(LATCH, GPIO.IN)
GPIO.setup(DATA,  GPIO.IN)

bits = []
current_buttons = []
last_printed = []
lock = threading.Lock()

def on_latch(channel):
    """Latch rising edge: start a new read cycle."""
    global bits
    with lock:
        bits = []

def on_clock(channel):
    """Clock falling edge: read one data bit."""
    global bits, current_buttons
    val = GPIO.input(DATA)
    with lock:
        bits.append(val)
        if len(bits) == 12:
            current_buttons = [BUTTONS[i] for i, b in enumerate(bits) if b == 0]

GPIO.add_event_detect(LATCH, GPIO.RISING, callback=on_latch)
GPIO.add_event_detect(CLOCK, GPIO.FALLING, callback=on_clock)

print("SNES passive tap (interrupt mode) — press buttons on the controller")
print("Ctrl+C to quit.\n")

try:
    while True:
        with lock:
            btns = list(current_buttons)
        if btns != last_printed:
            if btns:
                print("Pressed:", btns)
            last_printed = btns
        time.sleep(0.016)  # ~60Hz display rate
except KeyboardInterrupt:
    print("\nDone.")
finally:
    GPIO.cleanup()
