#!/usr/bin/env python3
"""Diagnostic: count signal transitions on all 3 GPIO pins for 5 seconds."""
import RPi.GPIO as GPIO
import time

CLOCK = 17
LATCH = 27
DATA  = 22

GPIO.setmode(GPIO.BCM)
GPIO.setup(CLOCK, GPIO.IN)
GPIO.setup(LATCH, GPIO.IN)
GPIO.setup(DATA,  GPIO.IN)

print("Reading GPIO for 5 seconds (SNES should be on)...")

transitions = {17: 0, 27: 0, 22: 0}
prev = {17: GPIO.input(CLOCK), 27: GPIO.input(LATCH), 22: GPIO.input(DATA)}

start = time.time()
while time.time() - start < 5:
    for pin in [CLOCK, LATCH, DATA]:
        val = GPIO.input(pin)
        if val != prev[pin]:
            transitions[pin] += 1
            prev[pin] = val

names = {17: "Clock", 27: "Latch", 22: "Data"}
print()
for pin in [CLOCK, LATCH, DATA]:
    state = "HIGH" if GPIO.input(pin) else "LOW"
    print(f"  GPIO {pin} ({names[pin]:5s}): {transitions[pin]:6d} transitions, currently {state}")

if transitions[27] > 0:
    print(f"\n  Latch rate: ~{transitions[27]//2}/sec (expect ~60 for 60fps game)")
if transitions[17] > 0:
    print(f"  Clock rate: ~{transitions[17]//2}/sec")

if transitions[17] == 0 and transitions[27] == 0 and transitions[22] == 0:
    print("\n  ** Still no signals. Try touching each wire to Pi Pin 1 (3.3V) to verify GPIO works.")

GPIO.cleanup()
