# The System-5 emulator in a GitHub Codespace

A Codespace is a computer in the cloud with this repository on it, opened in your browser. This repository sets one
up to run the System-5 emulator: nothing to install, and it works from any computer with a browser.

**There is no ELF/OS here.** ELF/OS, the disk operating system System-5 runs, is Mike Riley's work and carries no
permission to publish it, so it is not in this repository and the emulator runs with no CF card. Everything below the
operating system works: HBIOS's monitor, the screen and keyboard, the IO panel and the debugger. With an ELF/OS card
image of your own, see "Other ways to start it".

## Start it

1. On github.com, open the repository, then **Code -> Codespaces -> Create codespace on main**.
2. Wait for it to build: a few minutes the first time.
3. The emulator starts by itself and opens in a new browser tab. If the tab does not open, go to the **Ports** panel
   and click the globe beside **System-5 emulator** (port 8802).

The next time, use **Code -> Codespaces** and pick the same Codespace.

## Use it

- The **Machine** tab is the System-5: the 64 x 16 screen and the keyboard. Click the screen and type.
- The machine starts in HBIOS's monitor, at the `test>` prompt. The ROM is **HBIOS 1.0.6**, the real machine's since
  2026-11-15 (the line under the screen names it). `H` lists the monitor's commands: `?addr` shows memory,
  `!addr bb bb ..` writes it, `=src dst count` copies it, `@addr` runs from an address, `D start:end` disassembles
  (try `D F000:F040`; any key goes on at `-- more --`, Esc stops) and `Q1` / `Q0` turn Q on and off. `B` and
  **Boot ELF/OS** need an ELF/OS card.
- **Clock** sets the emulated CPU clock: as fast as the Codespace can go, 2 MHz, 1.76 MHz, or 500 kHz, the speed of
  the machine as it stands today.
- **Reset** is the CPU card's reset button.
- Below the screen is the **IO panel card**, designed for the new 36-pin System-5 but not built: eight LEDs and two hex
  displays that show what a program writes with `OUT 4`, eight toggles that `INP 4` reads, an **INPUT** button
  (EF1 while held), **RUN**, **LOAD**, and the Q light.
  To toggle a program in, as on a COSMAC ELF: RUN off, LOAD on; for each byte set the toggles and press INPUT; then
  LOAD off and RUN on, and it runs from 0000. Reset boots the ROM again. Try `E1 F8 20 A1 6C 64 21 30 04`: it copies
  the toggles to the LEDs.
- HBIOS has a panel demo built in: at `test>` type `@F1C0`. The LEDs follow the toggles and Q lights while INPUT is
  held, until Reset.
- The **Debugger** tab has the registers, the code at PC, memory, breakpoints and the debugger's command line
  (`help` lists the commands).

## Update, stop and restart

These go in the Codespace's terminal, the panel under the editor (**Ctrl-`** opens one if it is hidden). It starts in
the repository's top folder, which is where these commands expect to be run.

A Codespace keeps the copy of the repository it was made with. After something new is pushed to GitHub, three steps
bring it up to date:

    git pull
    software/s5emu/web-start.sh --stop
    software/s5emu/web-start.sh

Then reload the emulator's browser tab. If that tab was closed, open the **Ports** panel and click the globe beside
**System-5 emulator**. The last two lines alone restart the emulator without updating, for example after it hangs.

A refresh of the emulator's tab only shows the machine again, exactly where it was; it never restarts or updates it.
If the Codespace has stopped (30 minutes without use), start it again from **Code -> Codespaces**: that starts the
emulator too, at `test>`.

## Other ways to start it

Stop the emulator first (`software/s5emu/web-start.sh --stop`), then start it with a setting in front:

    S5_CLOCK=1.76m software/s5emu/web-start.sh

starts it with another clock (`max`, `2m`, `1.76m` or `500k`).

    S5_ROM=software/s5emu/roms/hbios-1.0.4.rom software/s5emu/web-start.sh

starts it with HBIOS 1.0.4, the ROM in the real machine until 2026-11-15.

    S5_PANEL=none software/s5emu/web-start.sh

starts it without the IO panel card.

    S5_DISK=/path/to/card.img software/s5emu/web-start.sh

starts it with a CF card image of your own (a raw image, as `dd` reads a card). `save` in the Debugger tab's command
line writes the card back to that file.

## Cost

A Codespace counts against your GitHub account's monthly Codespaces hours, and stops by itself after 30 minutes
without use. Stop or delete it from **Code -> Codespaces** when you are done.

## On a Mac

The same script works there:

    software/s5emu/web-start.sh --fg

then open http://127.0.0.1:8802/.
