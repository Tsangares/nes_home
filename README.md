# SNES Jr Smart Remote

A Raspberry Pi Zero W hidden inside a real SNES Jr shell, turning an original SNES controller into a smart home remote. Passively taps the controller's shift register to read button presses, then forwards them as smart light commands (MQTT) and Android TV navigation (ADB over WiFi).

```
   ┌─────────────────────────────────────────┐
   │            SNES Jr Shell                 │
   │                                          │
   │   ┌──────────┐      ┌──────────────┐    │
   │   │   SNES   │ GPIO │  Pi Zero W   │    │
   │   │Controller├──────┤              │    │
   │   │          │ tap  │  snes_read   │    │
   │   └──────────┘      │       │      │    │
   │                      │       ├──── MQTT ──────► Smart Lights
   │                      │       │      │    │
   │                      │       └──── ADB ───────► Android TV
   │                      └──────────────┘    │
   └─────────────────────────────────────────┘
```

## Button Map

```
  ┌───┐                               ┌───┐
  │ L │          SNES Jr               │ R │
  │PgU│                                │PgD│
  └───┘                                └───┘
     ┌─────────────────────────────────────┐
     │                                     │
     │       ┌───┐                         │
     │       │ ▲ │              ┌───┐      │
     │   ┌───┼───┼───┐    ┌───┐│ X │      │
     │   │ ◄ │   │ ► │    │ Y ││ 💡│      │
     │   └───┼───┼───┘    │💡2│├───┤      │
     │       │ ▼ │    SEL  └───┘│ A │      │
     │       └───┘    MENU      │ OK│      │
     │      D-PAD      START    └───┘      │
     │       TV        ⏻ TV      TV        │
     │                                     │
     │              ┌───┐                  │
     │              │ B │                  │
     │              │ ◄─┘                  │
     │              └───┘                  │
     └─────────────────────────────────────┘
```

| Button | Function | Target |
|--------|----------|--------|
| **D-pad** | Navigate (Up/Down/Left/Right) | Android TV |
| **A** | Select / Enter | Android TV |
| **B** | Back | Android TV |
| **Start** | Power On/Off | Android TV |
| **Select** | Menu | Android TV |
| **L** | Page Up | Android TV |
| **R** | Page Down | Android TV |
| **X** | Toggle Light 1 | Tasmota (MQTT) |
| **Y** | Toggle Light 2 | Tasmota (MQTT) |

## How It Works

The Pi doesn't replace the SNES — it **passively taps** the controller's serial bus. The SNES console drives Clock and Latch signals to poll the controller at ~60Hz. The Pi listens on those same lines (stepped down from 5V to 3.3V via voltage dividers) and reads the Data line on each clock edge, reconstructing which buttons are pressed.

Two services run on the Pi:

1. **`snes_read`** (C) — Reads the controller via direct GPIO memory-mapped I/O. Handles debouncing with a state machine (press/cooldown/release). Fires MQTT messages for light buttons (X/Y) and writes ADB keycodes to a FIFO pipe for TV buttons.

2. **`snes_adb_daemon`** (Python) — Reads keycodes from the FIFO and forwards them to the Android TV over a persistent ADB TCP connection using `adb-shell` (pure Python — the standard `adb` binary doesn't run on ARMv6).

## Wiring

Passive tap from the SNES controller port, through 1k/2k voltage dividers (5V -> 3.3V):

| SNES Pin | Signal | Pi Pin | GPIO |
|----------|--------|--------|------|
| 2 | Clock | 11 | 17 |
| 3 | Latch | 13 | 27 |
| 4 | Data | 15 | 22 |
| 7 | GND | 6 | GND |

## Setup

### 1. Configure credentials

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
nano .env
```

The `.env` file is gitignored and stores MQTT credentials, device topics, and the TV IP.

### 2. Build and install

```bash
# Compile the controller reader
gcc -O2 -o ~/snes_read ~/snes_read.c

# Install Python ADB library (no armv6 adb binary exists)
pip install adb-shell pure-python-adb --break-system-packages

# Generate ADB key (first time only)
mkdir -p ~/.android
python3 -c "from adb_shell.auth.keygen import keygen; keygen('$HOME/.android/adbkey')"
```

### 3. Systemd services

```bash
# Copy service files and .env
sudo cp snes-controller.service snes-adb.service /etc/systemd/system/
cp .env ~/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable --now snes-controller snes-adb
```

### 4. Android TV setup

Enable **Network Debugging** on the TV:
Settings > Device Preferences > Developer Options > Network Debugging: ON

The first ADB connection will prompt for authorization on the TV screen — accept it once and it stays trusted.

## Project Structure

```
snes_read.c              # Controller reader + MQTT + ADB FIFO (C)
snes_adb_daemon.py       # ADB bridge daemon (Python)
snes-controller.service  # Systemd unit for snes_read
snes-adb.service         # Systemd unit for ADB daemon
mqtt.md                  # MQTT broker config reference
CLAUDE.md                # Dev context
diag/                    # GPIO/serial diagnostic scripts
  controller_read.py     #   Python controller reader (interrupt-driven)
  gpio_test.py           #   Live GPIO pin monitor
  gpio_diag.py           #   Signal transition counter
  full_diag.py           #   Full GPIO pin scan
  test_serial.py         #   UART serial monitor
```

## Hardware

- **Pi**: Raspberry Pi Zero W Rev 1.1 (BCM2835, ARMv6l, 512MB)
- **OS**: Raspberry Pi OS (Bookworm)
- **Enclosure**: SNES Jr (SNS-101) shell
- **TV**: Onn Android TV (IP configured in `.env`)
- **Lights**: Tasmota smart plugs via MQTT (credentials in `.env`)
