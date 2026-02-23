#!/usr/bin/env python3
"""
Full diagnostic for SNES controller tap.
1. Scans ALL usable GPIO pins for any activity
2. Tests that our specific pins (17, 27, 22) can read HIGH/LOW
"""
import RPi.GPIO as GPIO
import time

# All usable BCM GPIO pins on Pi Zero W header
ALL_PINS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
            16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]

# Physical pin mapping for reference
BCM_TO_PHYS = {
    2:3, 3:5, 4:7, 5:29, 6:31, 7:26, 8:24, 9:21, 10:19, 11:23,
    12:32, 13:33, 14:8, 15:10, 16:36, 17:11, 18:12, 19:35, 20:38,
    21:40, 22:15, 23:16, 24:18, 25:22, 26:37, 27:13
}

GPIO.setmode(GPIO.BCM)

# Try to set up all pins as inputs
active_pins = []
for pin in ALL_PINS:
    try:
        GPIO.setup(pin, GPIO.IN)
        active_pins.append(pin)
    except Exception as e:
        print(f"  GPIO {pin:2d} (phys {BCM_TO_PHYS.get(pin,'?'):2}): BUSY/ERROR - {e}")

print(f"\n=== Scanning {len(active_pins)} GPIO pins for 5 seconds ===")
print("(SNES must be ON and running a game)\n")

transitions = {p: 0 for p in active_pins}
prev = {p: GPIO.input(p) for p in active_pins}
initial = dict(prev)

start = time.time()
while time.time() - start < 5:
    for pin in active_pins:
        val = GPIO.input(pin)
        if val != prev[pin]:
            transitions[pin] += 1
            prev[pin] = val

print(f"{'GPIO':>5} {'Phys':>5} {'Transitions':>12} {'Initial':>8} {'Final':>6}  Note")
print("-" * 60)
for pin in active_pins:
    phys = BCM_TO_PHYS.get(pin, "?")
    final = "HIGH" if GPIO.input(pin) else "LOW"
    init = "HIGH" if initial[pin] else "LOW"
    note = ""
    if pin == 17: note = "<-- CLOCK expected here"
    if pin == 27: note = "<-- LATCH expected here"
    if pin == 22: note = "<-- DATA expected here"
    if transitions[pin] > 0: note += " *** ACTIVITY ***"
    print(f"  {pin:3d}   {phys:3}   {transitions[pin]:10d}   {init:>5}  {final:>5}  {note}")

total = sum(transitions.values())
print(f"\nTotal transitions across all pins: {total}")
if total == 0:
    print("\nNo activity on ANY pin. Possible causes:")
    print("  1. SNES not actually running (needs a game cartridge inserted and powered on)")
    print("  2. Solder joints on SNES motherboard not making contact with traces")
    print("  3. Wires not actually reaching Pi header pins")
    print("  4. Try: measure Clock pin on SNES side (before divider) with multimeter")
    print("     - Should see ~2.5V average if toggling (not static 0V or 5V)")

GPIO.cleanup()
