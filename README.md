# SNES Jr Smart Remote

A Raspberry Pi Zero W hidden inside a real Super Nintendo Jr (SNS-101) shell that
turns an original SNES controller into a smart-home remote. The Pi **passively
taps** the controller's shift register — it reads the same wires the console
does, without interfering — and forwards button presses to smart lights over
**MQTT** and to an Android TV over **ADB**.

Press X to flip a lamp. Press the D-pad to scroll Netflix. Hold R to turn the TV
off. The controller still works as a normal SNES controller the whole time.

> 📷 See the [build gallery](images/) for the full teardown-to-assembly photo log.

![The Raspberry Pi Zero W and wiring tucked into the open SNES Jr shell beside the original motherboard.](images/11-2026-06-28-pi-mounted-snes-shell.jpg)

```
   ┌──────────────────────────────────────────────┐
   │               SNES Jr Shell                   │
   │                                               │
   │   ┌──────────┐   tap    ┌──────────────┐      │
   │   │   SNES   │ (passive)│  Pi Zero W   │      │
   │   │Controller├──────────┤              │      │
   │   │ shift reg│  5V→3.3V  │  snes_read   │      │
   │   └──────────┘  divider  │      │       │     │
   │                          │      ├── MQTT ──────┼──► Smart plugs
   │                          │      │       │      │
   │                          │      └── ADB ───────┼──► Android TV
   │                          └──────────────┘      │
   └───────────────────────────────────────────────┘
```

## Button Map

```
    [L PgUp]                            [R PgDn / hold=TV power]
  .-----------------------------------------------.
  |                                               |
  |      .---.                         (X)        |
  |      | ^ |                       Light 1      |
  |  .---+---+---.                                |
  |  | < |   | > |  (SEL)  (STA)  (Y)     (A)    |
  |  '---+---+---'  Menu   ----   Light2   OK     |
  |      | v |                                    |
  |      '---'                         (B)        |
  |      TV Nav                        Back       |
  |                                               |
  '-----------------------------------------------'
```

| Button | Action | Target |
|--------|--------|--------|
| **D-pad** | Navigate (Up / Down / Left / Right) | Android TV |
| **A** | Enter / select | Android TV |
| **B** | Back | Android TV |
| **Select** | Menu | Android TV |
| **L** | Page Up | Android TV |
| **R** (tap) | Page Down | Android TV |
| **R** (hold 3s) | Power on/off | Android TV |
| **X** | Toggle smart plug 1 | Tasmota (MQTT) |
| **Y** | Toggle smart plug 2 | Tasmota (MQTT) |
| **Start** | *(unused / free to remap)* | — |

## How It Works

The Pi doesn't replace or emulate the SNES — it **eavesdrops** on the
controller's serial bus. A standard SNES controller is just two 4021 shift
registers. Every frame (~60 Hz) the console pulses **Latch** to snapshot the
button states, then sends 16 **Clock** pulses; on each pulse the controller
shifts the next bit out on the **Data** line. The first 12 bits are the buttons.

The Pi listens on those same three lines (stepped down from 5 V to 3.3 V) and
reconstructs the button state by sampling Data on each clock edge:

```
Latch  ──┐_┌──────────────────────────────────────  (snapshot pulse, ~12 µs)
         │ │
Clock  ──┘ └─┐_┌─┐_┌─┐_┌─┐_┌─ ... ─┐_┌──────────────  (16 pulses)
              │   │   │   │          │
Data   ──────<B ><Y ><Sel><Sta> ... <R >─────────────  (active-LOW: 0 = pressed)
              0   1   2   3          11

Bit order: B, Y, Select, Start, Up, Down, Left, Right, A, X, L, R
```

Two services run on the Pi:

1. **`snes_read`** (C) — Reads the controller via direct, memory-mapped GPIO for
   tight timing. Each button runs a small debounce state machine
   (press → fire → cooldown → wait-for-release) so a single noisy frame can't
   register as a press. Light buttons (X/Y) fire MQTT messages; TV buttons write
   ADB keycodes into a FIFO.

2. **`snes_adb_daemon`** (Python) — Drains the FIFO and forwards each keycode to
   the Android TV over a persistent ADB-over-TCP connection using `adb-shell`
   (pure Python — there's no `adb` binary for ARMv6, so the standard tool won't
   run on a Pi Zero W).

### A note on debouncing (the "ghost press" fix)

Because this is a *passive* tap, the last bit clocked out (**R**, bit 11) is the
most exposed to electrical noise and timing skew. An earlier build added an
"R tap vs. R hold" feature that armed on a *single* frame, so a lone glitch on
that last bit fired a phantom Page-Down roughly every 20 seconds. The fix:
require several consecutive confirmed-pressed frames (`R_PRESS_FRAMES`) before
arming R, matching how every other button is debounced. Glitch gone.

## Wiring

Passive tap from the controller's extension cable. Each signal line passes
through a **bidirectional logic-level-shifter module** to drop the SNES's 5 V
logic to a GPIO-safe 3.3 V (the high side ties to 5 V, the low side to the Pi's
3.3 V rail):

```
  SNES 5V signal ──► [ HV ]  level     [ LV ] ──► Pi GPIO (3.3V)
                              shifter
       5V rail ───► HV-VCC   module    LV-VCC ◄─── Pi 3.3V rail
          GND ────────────── common ─────────────── Pi GND
```

| SNES Pin | Signal | Pi Header Pin | GPIO | Direction |
|----------|--------|---------------|------|-----------|
| 2 | Clock | 11 | 17 | read (passive) |
| 3 | Latch | 13 | 27 | read (passive) |
| 4 | Data  | 15 | 22 | read (passive) |
| 7 | GND   | 6  | —  | common ground |

> The Pi reads all three lines — the **console** drives Clock and Latch. Make
> sure the Pi and SNES share a common ground or the readings will be garbage.

> **Alternative:** discrete 1 kΩ / 2 kΩ resistor dividers per line
> (`Vout = 5V × 2k/(1k+2k) ≈ 3.3V`) also work for a read-only tap; the module
> is just tidier and handles all three lines on one board.

![Tap wires soldered to the underside of the SNES controller PCB.](images/14-2026-06-28-snes-controller-pcb.jpg)
*Tap wires soldered to the controller PCB's Clock / Latch / Data traces.*

![The level-shifter module wired between the controller signals and the Pi GPIO.](images/13-2026-06-28-level-shifter-module.jpg)
*The level-shifter module dropping the controller's 5V signals to 3.3V.*

## Setup

### 1. Configure credentials

```bash
cp .env.example .env
nano .env        # MQTT broker + topics, Android TV IP
```

`.env` is gitignored and holds your broker credentials, the two Tasmota topics,
and the TV's address. See [`mqtt.md`](mqtt.md) for the MQTT side.

### 2. Build and install

```bash
# Compile the controller reader
gcc -O2 -o ~/snes_read ~/snes_read.c

# Pure-Python ADB (no armv6 adb binary exists)
pip install adb-shell --break-system-packages

# Generate an ADB key (first time only)
mkdir -p ~/.android
python3 -c "from adb_shell.auth.keygen import keygen; keygen('$HOME/.android/adbkey')"
```

### 3. Systemd services

The unit files assume user `pi` and `/home/pi` — edit `User`, `Group`, and the
paths to match your account before installing.

```bash
sudo cp snes-controller.service snes-adb.service /etc/systemd/system/
cp .env ~/

sudo systemctl daemon-reload
sudo systemctl enable --now snes-controller snes-adb
```

### 4. Android TV

Enable **Network Debugging** on the TV:
`Settings → Device Preferences → Developer Options → Network Debugging: ON`.
The first ADB connection pops an authorization prompt on the TV — accept it once
and it stays trusted.

## Troubleshooting

```bash
# Watch live button events
journalctl -u snes-controller -f

# See what the TV bridge is doing
journalctl -u snes-adb -f
```

- **Phantom presses?** Check your common ground and the divider resistor values,
  then bump `R_PRESS_FRAMES` / `PRESS_FRAMES` in `snes_read.c`.
- **No events at all?** The console must be powered and polling — the Pi only
  reads, it never drives the bus.
- **TV not responding?** Confirm the IP in `.env`, that Network Debugging is on,
  and re-accept the ADB prompt on screen.

## Project Structure

```
snes_read.c              # Controller reader + MQTT + ADB FIFO (C)
snes_adb_daemon.py       # ADB bridge daemon (Python)
snes-controller.service  # systemd unit for snes_read
snes-adb.service         # systemd unit for the ADB daemon
.env.example             # Credential template (copy to .env)
mqtt.md                  # MQTT topic reference
images/                  # Build photos (add your own)
diag/                    # GPIO/serial diagnostic scripts
  controller_read.py     #   Python controller reader (interrupt-driven)
  gpio_test.py           #   Live GPIO pin monitor
  gpio_diag.py           #   Signal transition counter
  full_diag.py           #   Full GPIO pin scan
  test_serial.py         #   UART serial monitor
```

## Hardware

- **Pi**: Raspberry Pi Zero W Rev 1.1 (BCM2835, single-core ARMv6, 512 MB RAM)
- **OS**: Raspberry Pi OS
- **Enclosure**: SNES Jr (SNS-101) shell
- **TV**: Android TV with Network Debugging enabled
- **Lights**: Tasmota smart plugs over MQTT

## License

[MIT](LICENSE) © Tsangares
