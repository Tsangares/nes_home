# Build Gallery

Photos and clips from the build, in chronological order. Metadata (EXIF/GPS)
has been stripped from every file, and filenames are `NN-YYYY-MM-DD-subject`.

## Teardown — Feb 2026

![Super Nintendo Jr with a Donkey Kong Country cartridge and two controller ports, on carpet.](01-2026-02-18-snes-console-with-cartridge.jpg)
*01 — The starting point: a stock SNES Jr with a cartridge loaded.*

🎬 [02 — clip: the unmodified console before the Pi goes in](02-2026-02-18-snes-console-cartridge-demo.mp4)

![Disassembled SNES controller showing the open shell halves and internal PCB with button contacts exposed.](03-2026-02-19-snes-controller-pcb-internals.jpg)
*03 — The SNES controller opened up: shell halves and the button-contact PCB.*

![Interior of the opened SNES Jr shell: cartridge-slot connector, shielded mainboard, and controller-port connectors.](04-2026-02-19-snes-console-shell-interior.jpg)
*04 — Inside the console shell — cartridge slot, shielded mainboard, controller ports.*

![SNES Jr console with the top shell removed, exposing the main PCB and shielding.](05-2026-02-19-snes-console-disassembled.jpg)
*05 — Top shell off, main PCB exposed.*

![The SNES Jr mainboard SNN-CPU-01 (1997) with its CPU, PPU, and RAM chips.](06-2026-02-19-snes-console-mainboard.jpg)
*06 — The SNES Jr mainboard (SNN-CPU-01, 1997).*

🎬 [07 — clip: console with cartridge and controller cable on the front port](07-2026-02-22-snes-console-cables-setup.mp4)

## Reassembled — Mar–Apr 2026

![The reassembled SNES Jr shell with cartridge and controller.](08-2026-03-01-snes-jr-assembled.jpg)
*08 — Buttoned back up with cartridge and controller.*

![A hand holding an original SNES controller plugged into the SNES Jr console.](09-2026-04-04-snes-controller-and-console.jpg)
*09 — Original controller plugged in and working.*

## Pi integration — Jun 2026

![The SNES console with cartridge and controller on a wooden surface.](10-2026-06-28-snes-console-and-controller.jpg)
*10 — Console and controller, ready for the Pi tap.*

![The open SNES Jr shell beside its controller, Pi Zero W and wiring tucked in next to the original motherboard.](11-2026-06-28-pi-mounted-snes-shell.jpg)
*11 — Pi Zero W and wiring tucked in alongside the original motherboard.*

![Raspberry Pi Zero W inside the open shell with GPIO jumper wires on its 40-pin header.](12-2026-06-28-pi-zero-gpio-wiring.jpg)
*12 — GPIO jumpers on the Pi's 40-pin header.*

![A breakout module wired inside the shell that level-shifts 5V controller signals to 3.3V for the Pi.](13-2026-06-28-level-shifter-module.jpg)
*13 — The level-shifter module dropping the 5V controller signals to 3.3V.*

![Underside of the SNES controller PCB with tap wires soldered to its signal traces.](14-2026-06-28-snes-controller-pcb.jpg)
*14 — Tap wires soldered to the controller PCB's Clock / Latch / Data traces.*

![Pi Zero W beside the open SNES Jr motherboard, level-shifter module and wires bridging the controller-port signals.](15-2026-06-28-pi-level-shifter-wiring.jpg)
*15 — The full passive tap wired up: controller signals → level shifter → Pi GPIO.*
