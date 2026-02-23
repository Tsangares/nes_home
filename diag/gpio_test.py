#!/usr/bin/env python3
"""Live GPIO monitor - watch for any signal on the controller pins."""
import RPi.GPIO as GPIO
import time

CLOCK = 17  # Pin 11
LATCH = 27  # Pin 13
DATA  = 22  # Pin 15

GPIO.setmode(GPIO.BCM)
GPIO.setup(CLOCK, GPIO.IN)
GPIO.setup(LATCH, GPIO.IN)
GPIO.setup(DATA,  GPIO.IN)

print("Live GPIO monitor - 60 seconds")
print("With SNES on: watch for changes")
print("Or: touch a wire to 3.3V (Pi Pin 1) or GND (Pi Pin 6) to test")
print()

last = ""
start = time.time()
try:
    while time.time() - start < 60:
        c = GPIO.input(CLOCK)
        l = GPIO.input(LATCH)
        d = GPIO.input(DATA)
        line = f"Clock(17)={c}  Latch(27)={l}  Data(22)={d}"
        if line != last:
            print(f"[{time.time()-start:5.1f}s] {line}  <-- CHANGED")
            last = line
        time.sleep(0.005)
except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()
    print("\nDone.")
