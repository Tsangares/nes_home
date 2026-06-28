# SNES Jr Smart Remote — Build Log

**Date:** 2026-06-28
**Milestone:** Controller tap working end-to-end, ghost-press bug fixed, repo cleaned up and documented for public release.

A Raspberry Pi Zero W hidden inside a real Super Nintendo Jr (SNS-101) shell turns
an original SNES controller into a smart-home remote. The Pi **passively taps**
the controller's serial bus — it reads the same three wires the console does,
without interfering — and forwards button presses to smart lights over MQTT and
to an Android TV over ADB. The controller still works as a normal SNES controller
the whole time.

Repo: https://github.com/Tsangares/nes_home

---

## The idea

A SNES controller is just two 4021 shift registers. Every frame (~60 Hz) the
console pulses **Latch** to snapshot the buttons, then sends 16 **Clock** pulses;
on each pulse the controller shifts the next bit out on **Data**. The first 12
bits are the buttons (active-LOW: `0` = pressed).

```
Latch  ──┐_┌──────────────────────────────────────  (snapshot pulse, ~12 µs)
Clock  ──┘ └─┐_┌─┐_┌─┐_┌─ ... ─┐_┌──────────────────  (16 pulses)
Data   ──────<B ><Y ><Sel> ... <R >─────────────────  (0 = pressed)
              0   1   2          11

Bit order: B, Y, Select, Start, Up, Down, Left, Right, A, X, L, R
```

So instead of building a controller adapter, I just **eavesdrop**: wire the Pi
onto Clock/Latch/Data alongside the console, sample Data on each clock edge, and
reconstruct the button state. Buttons then map to actions:

- **X / Y** → toggle two Tasmota smart plugs (MQTT)
- **D-pad / A / B / Select / L** → Android TV navigation (ADB keycodes)
- **R tap** → Page Down; **R hold 3s** → TV power

## Hardware

- Raspberry Pi Zero W Rev 1.1 (BCM2835, single-core ARMv6, 512 MB)
- SNES Jr (SNS-101) shell + an original SNES controller
- A **bidirectional logic-level-shifter module** to drop the SNES's 5 V signals
  to the Pi's 3.3 V GPIO (discrete 1k/2k dividers would also work for a read-only
  tap, but the module is tidier and handles all three lines on one board)
- Common ground between the Pi and the SNES — non-negotiable, or the reads are garbage

| SNES Pin | Signal | Pi Header Pin | GPIO | Pi direction |
|---|---|---|---|---|
| 2 | Clock | 11 | 17 | input (read) |
| 3 | Latch | 13 | 27 | input (read) |
| 4 | Data  | 15 | 22 | input (read) |
| 7 | GND   | 6  | —  | common ground |

## Software stack (with versions)

**On the Pi** (Raspbian GNU/Linux 13 trixie, kernel `6.12.47+rpt-rpi-v6`):

| Tool | Version | Role |
|---|---|---|
| Python | 3.13.5 | ADB bridge daemon |
| gcc | 14.2.0 (Raspbian 14.2.0-19+rpi1) | builds `snes_read.c` |
| adb-shell | 0.4.4 | pure-Python ADB (no `adb` binary exists for ARMv6) |
| gpiod | 2.2.0 | (diagnostics) |
| mosquitto-clients | `mosquitto_pub` | fire-and-forget MQTT publish |

**On the workstation** (for the photo/repo cleanup): gcc 16.1.1, ffmpeg
n8.1.1, ImageMagick 7.1.2-24, libjpeg-turbo 3.1.4.1 (`jpegtran`), git 2.54.0.

### Architecture — two services

1. **`snes_read`** (C, `~640` lines compiled with `gcc -O2`) — reads the
   controller via direct memory-mapped GPIO (`/dev/gpiomem`) for tight timing.
   Each button runs a small debounce state machine (press → fire → cooldown →
   wait-for-release). X/Y fork `mosquitto_pub`; TV buttons write ADB keycodes
   into a FIFO at `/tmp/snes_adb`.
2. **`snes_adb_daemon.py`** (Python) — drains the FIFO and forwards each keycode
   to the Android TV over a persistent ADB-over-TCP connection via `adb-shell`.

Both run as `systemd` units (`snes-controller.service`, `snes-adb.service`),
enabled and restarting-on-failure, so the whole thing comes back after a reboot.

## Build timeline

Photos in [`../images/`](../images/) (chronological, `NN-YYYY-MM-DD-subject`):

- **Feb 18–22** — Teardown. Opened the SNES Jr shell and the controller, mapped
  the mainboard (SNN-CPU-01, 1997) and the controller's button-contact PCB.
- **Mar–Apr** — Reassembled and confirmed the console + controller still work
  normally (the tap has to be non-destructive).
- **Jun 28** — Pi integration: soldered tap wires onto the controller PCB's
  Clock/Latch/Data traces, wired them through the level-shifter module to the
  Pi's GPIO header, and tucked the Pi Zero W into the shell alongside the
  original motherboard.

## The bug hunt: a ghosting D-pad

**Symptom:** the TV kept scrolling on its own — what looked like a phantom
"D-pad down."

**Diagnosis (from the logs):**

```bash
journalctl -u snes-controller.service --since '6 hours ago' --no-pager \
  | grep -oE '[A-Za-z]+ tap → KEYCODE_[A-Z_]+' | sort | uniq -c | sort -rn
#   1037 R tap → KEYCODE_PAGE_DOWN
```

1,037 events in 6 hours — **every single one** `R tap → KEYCODE_PAGE_DOWN`, ~3
per minute, with zero real button presses. So it wasn't the D-pad at all: it was
the **R shoulder button** (mapped to Page-Down, which scrolls a TV menu *down* and
reads as "D-pad down").

**Root cause:** a recently added "R tap vs. R hold-3s-for-power" feature armed on
a **single frame** — no debounce. `R` is bit 11, the *last* bit clocked out of the
shift register and the most exposed to electrical noise/timing skew on a passive
tap. One glitchy low read on that last bit fired a phantom Page-Down.

**Fix:** debounce R the same way every other button already was — require
`R_PRESS_FRAMES` (4) consecutive confirmed-pressed frames before arming:

```c
case RH_IDLE:
    if (r_pressed) {
        rh_press_count++;
        if (rh_press_count >= R_PRESS_FRAMES) { rh_state = RH_HELD; rh_hold_start = t; rh_press_count = 0; }
    } else {
        rh_press_count = 0;          /* a lone glitch frame resets the count */
    }
    break;
```

**Verification:** rebuilt, restarted, and watched the logs — **0 phantom events**
since the debounced build, including across an unplanned reboot. Was ~3/min before.

## Other gotchas

- **No `adb` binary for ARMv6.** The stock Android Platform Tools don't ship an
  armv6 build, so the Pi Zero W can't run `adb` directly. Solution: `adb-shell`
  (pure Python) over TCP. First connect prompts for authorization on the TV
  screen; accept once and it stays trusted.
- **`serial-getty` on the UART.** Had to disable the serial console
  (`serial-getty@ttyS0`) and drop `console=serial0,115200` from cmdline before
  the GPIO/serial pins were usable for the project.
- **Flaky power.** The Pi's power joint is still marginal — it dropped off the
  network mid-session and rebooted. The enabled systemd units meant the service
  (and the fix) came right back. Finalizing that solder joint is on the list.
- **Docs vs. reality: level shifter, not dividers.** The original notes described
  1k/2k resistor dividers, but the actual build uses a logic-level-shifter module.
  Caught it while auto-captioning the build photos — the vision pass flagged a
  "4-channel level shifter" where the docs said "divider." Docs corrected.
- **GPS in every photo.** The Pixel build photos had EXIF GPS pinning my home
  address. Stripped all of it (`jpegtran -copy none`) before anything went public.

## Repo cleanup for public release

- Scrubbed LAN IPs, Tasmota device IDs, and host paths/username from all tracked
  files; genericized the systemd units and `.env.example`. Verified no secret was
  ever committed (`.env` was always gitignored; the live MQTT password appears
  nowhere in history).
- Stripped metadata from 13 photos + 2 clips, renamed them chronologically, and
  auto-captioned them. Then **web-optimized**: resized photos to ≤1600 px JPEGs
  and transcoded the clips to 720p — the gallery went from **60 MB → 6 MB**. The
  full-size blobs were kept out of history by amending rather than adding a commit.

Key commands:

```bash
# strip EXIF/GPS losslessly + drop embedded motion-photo video
jpegtran -copy none -optimize in.jpg > out.jpg

# web-resize photos
mogrify -resize '1600x1600>' -quality 82 -strip *.jpg

# transcode a clip for the web
ffmpeg -i in.mp4 -vf scale=-2:720 -c:v libx264 -crf 28 -preset slow \
  -c:a aac -b:a 96k -movflags +faststart out.mp4

# rebuild + restart on the Pi
ssh pi@<pi-ip> "gcc -O2 -o ~/snes_read ~/snes_read.c && \
  sudo systemctl restart snes-controller"

# watch button events live
ssh pi@<pi-ip> "journalctl -u snes-controller -f"
```

## Open items

- [ ] Finalize the Pi's **power solder joint** (currently flaky).
- [ ] Move to the **headerless Pi Zero W** for the final in-shell build.
- [ ] **Start** button is currently unmapped — free to remap.
- [ ] If more video gets added, move media to **Git LFS** to keep clones light.
- [ ] Optional: confirm long-term stability of the R debounce under heavy use.

*Code snapshot at this milestone: [`code/`](code/). IPs/credentials are
read from a gitignored `.env`; nothing sensitive is checked in.*
