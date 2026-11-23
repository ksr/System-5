# Author: Claude (Anthropic) for Ken Rother's System-5 project, 2026-10-06
"""System-5 emulator.  python3 -m s5emu [options]   (run from software/s5emu)

Defaults: CPU card ROM = roms/hbios-1.0.6.rom, the machine's ROM since 2026-11-15 (HBIOS + Mike Riley's BIOS 1.0.4,
F000-FFFF, plus the monitor commands H, B, D and Q1 / Q0 and the disk calls always in LBA mode; built by
firmware/hbios/v1.0.6/build.py). --rom roms/hbios-1.0.5.rom or roms/hbios-1.0.4.rom runs an earlier one;
firmware/hbios/v0.9/sec1.rom is the older BIOS 0.9 build. --rom roms/hbios-1.0.7.rom runs v1.0.7 (2026-11-17, burned
that day): v1.0.6 plus @F1E0, which shows each key's code (0x31) on the bottom line.
Memory card jumpered RAM 0000-6FFF / open 7000 (video) / ROM 8000-EFFF, symbols from the ROM's listings.
"""
import argparse, os, sys
from .machine import Machine
from .shell import Shell

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
ROM104 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "roms", "hbios-1.0.4.rom")    # tools/mkrom.py
ROM105 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "roms", "hbios-1.0.5.rom")    # firmware/hbios/v1.0.5/build.py
DEF_ROM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "roms", "hbios-1.0.6.rom")   # firmware/hbios/v1.0.6/build.py
ROM107 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "roms", "hbios-1.0.7.rom")    # firmware/hbios/v1.0.7/build.py
VG_ROM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "roms", "hbios-video-g.rom")  # firmware/hbios/video-g/build.py
SYMS_104 = [os.path.join(ROOT, "firmware/hbios/v0.9/sec1.lst"), os.path.join(ROOT, "firmware/hbios/v1.0.4/orig_bios/bios.lst")]
# symbols for each of these ROMs, whichever is the default: 1.0.5 and 1.0.6 are 1.0.4 byte for byte plus new code in
# bytes 1.0.4 leaves empty (and 1.0.6's two 3-byte jumps at FBC1 / FBDF), so 1.0.4's listings hold for them too, and
# each one's own listing adds the new code (monext, the disassembler, ...)
ROM_SYMS = {os.path.realpath(ROM104): SYMS_104,
            os.path.realpath(ROM105): [os.path.join(ROOT, "firmware/hbios/v1.0.5/sec1.lst")] + SYMS_104,
            os.path.realpath(DEF_ROM): [os.path.join(ROOT, "firmware/hbios/v1.0.6/sec1.lst")] + SYMS_104,
            os.path.realpath(ROM107): [os.path.join(ROOT, "firmware/hbios/v1.0.7/sec1.lst")] + SYMS_104}


def parse_jumpers(text):
    """16 characters, one per 4K block from 0000: R = RAM, E = EPROM (ROM), - = open.  e.g. RRRRRRR-EEEEEEE-"""
    t = text.strip().upper()
    if len(t) != 16 or set(t) - set("RE-"): raise SystemExit("--jumpers needs 16 of R/E/-")
    return [{"R": "RAM", "E": "ROM", "-": None}[c] for c in t]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="s5emu", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rom", default=DEF_ROM, help="CPU card EPROM image (hex or bin at --rom-base)")
    ap.add_argument("--rom-base", default="F000", help="CPU card EPROM address (hex, default F000)")
    ap.add_argument("--romhi", help="memory-card EPROM image (Intel hex, or binary loaded at 8000)")
    ap.add_argument("--load", action="append", default=[], help="FILE[@ADDR] into RAM before starting")
    ap.add_argument("--disk", help="IDE/CF disk image file (created 32 MB if missing; 'save' writes it back)")
    ap.add_argument("--jumpers", default="RRRRRRR-EEEEEEE-", help="memory-card 4K blocks from 0000: R/E/- (default RRRRRRR-EEEEEEE-)")
    ap.add_argument("--sym", action="append", default=[], help="symbols from an rcasm/A18 listing (repeatable)")
    ap.add_argument("--pixie-port", type=int, default=4, help="1861 I/O port (INP = on, OUT = off; default 4)")
    ap.add_argument("--buslink", action="store_true", help="open a pty speaking the bus driver card's protocol (for s5busdrv.py --port): BUSDRV-C's with --hw --cpu-rev D (the modes, LOAD mode, the 36-pin lines), else BUSDRV-B's")
    ap.add_argument("--buslink-rev", choices=("B", "C"), help="--buslink: which card, whatever the machine (C needs CPU Rev D)")
    ap.add_argument("--hw", action="store_true", help="hardware-faithful bus: memory card from its KiCad netlist, contention logged (see s5emu/hw.py)")
    ap.add_argument("--mem-rev", default="D", help="--hw memory card: D (card of record), F (MEM3-F: Rev E with EEPROM sockets and its silkscreen fixed; 27C256s), "
                    "F-28C256 (a 28C256 in IC5, read-only), F-28C256-W (the CPU can write it), C, B-built (Ken's reworked board), B-drawn")
    ap.add_argument("--cpu-rev", default="A-built", help="--hw CPU card: A-built (Ken's reworked board, the default), A (as drawn), D (CPU Rev D, the 36-pin card, not built) or none (behavioural -VMA)")
    ap.add_argument("--front", default=None, help="with --hw --cpu-rev D --panel A: fit the front panel (A) on the IO panel card's ribbon, from its netlist: "
                    "displays, LEDs, toggles, RUN, LOAD, INPUT and a RESET button that boots the EPROM (the debugger's 'front' command)")
    ap.add_argument("--panel", default=None, help="fit the IO panel card (A): port 4 LEDs/TIL311s/toggles, INPUT on -EF1, RUN/LOAD; the 1861 comes off port 4 (with --hw: from its netlist, use with --cpu-rev D)")
    ap.add_argument("--video-rev", default="B", help="--hw 6845 card from its netlist: B (the card in the machine, the default), B-Clean, "
                    "B-Clean-Keyboard (the PS/2 keyboard on the card, key at 7802 and status at 7804: use it with the VIDEO-G HBIOS; no IO card then), or none (behavioural)")
    ap.add_argument("--ide-rev", default="A", help="--hw IDE card: A (from its netlist, the default) or none (behavioural)")
    ap.add_argument("--io-rev", default="A", help="--hw IO card (1861 + keyboard): A (from its netlist, the default) or none (behavioural)")
    ap.add_argument("--vma", default="remap", choices=["remap", "boot", "norom"], help="--hw CPU card SV5 VMA mode (default remap = Boot/REMAP)")
    ap.add_argument("--bus-stop", default="", help="--hw: stop the debugger on these bus events, comma list of fight,double,multi-write,undefined")
    ap.add_argument("--video", default="6845", choices=["6845", "g", "G", "kbd"], help="video card: 6845 (the 6845 card + IO card, the default), g (VIDEO-G 1.0 in their place: s5emu/videog.py, "
                    "and with --hw its TEXT and GFX boards from their netlists, s5emu/hwvideog.py; ROM defaults to roms/hbios-video-g.rom; --panel A may be fitted with it: VIDEO-G uses no port) "
                    "or kbd (the 6845 card Rev B-Clean-Keyboard in their place: Rev B's video with the PS/2 keyboard on the card, key at 7802, status at 7804; "
                    "with --hw from its netlist; the same ROM default, and --panel A may be fitted)")
    ap.add_argument("--monitor", default="ntsc", choices=["ntsc", "mda"], help="--video g: the MONITOR jumper, ntsc (512 x 200, default) or mda (IBM 5151, 512 x 256)")
    ap.add_argument("--no-gfx", action="store_true", help="--video g: the TEXT board alone (no GFX board; with --hw, the ribbon unplugged)")
    ap.add_argument("--videog-rev", default="1.0", help="--hw --video g: 1.0 (TEXT and GFX from their netlists, the default) or none (the behavioural model on the modelled bus)")
    ap.add_argument("--kbd-flag", default="ef", choices=["ef", "ef1", "ef2", "ef3", "none"], help="--hw --video g (TEXT's JP3) or --video-rev B-Clean-Keyboard (its JP1): KBD FLAG, the bus line KEY-READY pulls low: ef (-EF, as set), ef1, ef2, ef3 or none (no shunt)")
    ap.add_argument("--ui", choices=["tui", "web", "none"], default="tui")
    ap.add_argument("--web-port", type=int, default=8802)
    ap.add_argument("--web-host", default="127.0.0.1", help="--ui web: address to listen on (0.0.0.0 = every interface)")
    ap.add_argument("--run", action="store_true", help="--ui web: start running at once (boots the ROM to its prompt)")
    ap.add_argument("--clock", help="emulated clock, e.g. 500k, 1.76m, 2m or max (sets --speed: a machine cycle is 8 clocks)")
    ap.add_argument("--speed", type=float, default=0, help="throttle to N machine cycles/s (1.79 MHz 1802 = 223750; 0 = flat out)")
    ap.add_argument("--script", help="run debugger commands from a file (one per line), print the output, then start the UI")
    ap.add_argument("-c", "--command", action="append", default=[], help="run one debugger command (repeatable); with --ui none the emulator exits after")
    a = ap.parse_args(argv)
    if a.clock:
        from .web import parse_clock, CYCLE_CLOCKS
        try: hz = parse_clock(a.clock)
        except ValueError as e: ap.error("--clock: %s" % e)
        a.speed = hz / CYCLE_CLOCKS if hz else 0

    front = None if not a.front or a.front.lower() == "none" else a.front.upper()
    if front and not (a.hw and a.panel and a.panel.lower() != "none"): raise SystemExit("--front needs --hw and --panel A (it hangs on that card's ribbon)")
    vg = a.video.lower() == "g"; vk = a.video.lower() == "kbd"
    rom = VG_ROM if ((vg or vk) and a.rom == DEF_ROM) else a.rom
    kw = dict(cpu_rom=rom, rom_base=int(a.rom_base, 16), jumpers=parse_jumpers(a.jumpers), disk=a.disk, pixie_port=a.pixie_port)
    if vg:                                             # VIDEO-G in place of the 6845 card and the IO card: no 1861; it is
        kw.pop("pixie_port")                           # memory-mapped (2026-11-17), so the IO panel keeps port 4 beside it
        if a.panel and a.panel.lower() not in ("none", "a"): raise SystemExit("--panel: A (the only revision) or none")
        panel = bool(a.panel) and a.panel.lower() == "a"
        if a.hw:
            from .hw import HWMachine
            m = HWMachine(mem_rev=a.mem_rev, vma_mode=a.vma, cpu_rev=None if a.cpu_rev.lower() == "none" else a.cpu_rev,
                          ide_rev=None if a.ide_rev.lower() == "none" else a.ide_rev, panel_rev="A" if panel else None, front_rev=front,
                          videog=a.videog_rev, monitor=a.monitor, gfx=not a.no_gfx,
                          kbd_flag=None if a.kbd_flag == "none" else "-" + a.kbd_flag.upper(),
                          mhz=2.0 if a.cpu_rev.upper() == "D" else 1.76, **kw)
            m.stop_on = {k for k in a.bus_stop.split(",") if k}
            print(m.describe(), file=sys.stderr)
        else:
            from .videog import VideoGMachine
            m = VideoGMachine(monitor=a.monitor, gfx=not a.no_gfx, panel=panel, **kw)
    elif vk:                                           # the 6845 card with the keyboard on it: no IO card, no 1861
        kw.pop("pixie_port")
        if a.panel and a.panel.lower() not in ("none", "a"): raise SystemExit("--panel: A (the only revision) or none")
        panel = bool(a.panel) and a.panel.lower() == "a"
        if a.hw:
            from .hw import HWMachine
            m = HWMachine(mem_rev=a.mem_rev, vma_mode=a.vma, cpu_rev=None if a.cpu_rev.lower() == "none" else a.cpu_rev,
                          video_rev="B-Clean-Keyboard", ide_rev=None if a.ide_rev.lower() == "none" else a.ide_rev,
                          panel_rev="A" if panel else None, front_rev=front, kbd_flag=None if a.kbd_flag == "none" else "-" + a.kbd_flag.upper(), **kw)
            m.stop_on = {k for k in a.bus_stop.split(",") if k}
            print(m.describe(), file=sys.stderr)
        else:
            from .machine import Video6845KbdMachine
            m = Video6845KbdMachine(panel=panel, **kw)
    elif a.hw:
        from .hw import HWMachine
        m = HWMachine(mem_rev=a.mem_rev, vma_mode=a.vma, cpu_rev=None if a.cpu_rev.lower() == "none" else a.cpu_rev, video_rev=None if a.video_rev.lower() == "none" else a.video_rev,
                      ide_rev=None if a.ide_rev.lower() == "none" else a.ide_rev,
                      io_rev=None if a.io_rev.lower() == "none" else a.io_rev, panel_rev=None if not a.panel or a.panel.lower() == "none" else a.panel, front_rev=front,
                      kbd_flag=None if a.kbd_flag == "none" else "-" + a.kbd_flag.upper(), **kw)   # (the 6845 card Rev B-Clean-Keyboard's JP1)
        m.stop_on = {k for k in a.bus_stop.split(",") if k}
        print(m.describe(), file=sys.stderr)
    else:
        if a.panel and a.panel.lower() not in ("none", "a"): raise SystemExit("--panel: A (the only revision) or none")
        m = Machine(panel=a.panel and a.panel.lower() == "a", **kw)
    if a.romhi: m.load_rom(a.romhi)
    for spec in a.load:
        f, _, at = spec.partition("@"); m.load_ram(f, int(at, 16) if at else None)
    sh = Shell(m)
    for f in (a.sym or ([] if (vg or vk) else ROM_SYMS.get(os.path.realpath(a.rom), []))):
        if os.path.exists(f): sh.d.load_symbols(f)
    running = [False]
    if a.buslink:
        from .buslink import BusLink
        try: sh.link = BusLink(m, lambda: running[0], rev=a.buslink_rev)
        except ValueError as e: raise SystemExit("--buslink-rev C: %s" % e)
        print("bus-driver link (BUSDRV-%s) on" % sh.link.rev, sh.link.path, file=sys.stderr)
    lines = list(a.command)
    if a.script: lines = open(a.script).read().splitlines() + lines
    for line in lines:
        if line.strip() == "c": print(sh.d.run(max_instructions=50_000_000)); continue
        out = sh.exec(line)
        if out: print(out)
    if a.ui == "tui":
        from . import tui; tui.run(sh, a.speed or None)
    elif a.ui == "web":
        from . import web; web.serve(sh, a.web_port, a.speed or None, running, host=a.web_host, run=a.run)
    if a.disk: m.ide.save()


if __name__ == "__main__":
    main()
