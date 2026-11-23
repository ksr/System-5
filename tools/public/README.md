# The public repository: github.com/ksr/System-5

System-5 has two repositories (Ken, 2026-11-15):

| | | |
|---|---|---|
| `ksr/elf` | private | the working repository: every change is made here, with Claude's notes (`CLAUDE.md`) and the history, which still holds the third-party files |
| `ksr/System-5` | public | a copy of elf's publishable files, made by `export.py` from an elf commit; published 2026-11-16, starting fresh, with no history from elf |

Third-party material is in neither: it is in the private repository `private-resources`, beside them, under `elf/`
(the README's "Kept private" section).

## Making and updating it

    python3 tools/public/export.py                                    scan only
    python3 tools/public/export.py --out ../System-5                  write ../System-5 (git init the first time)
    python3 tools/public/export.py --out ../System-5 --commit "..."   and commit there

Then, after a look at what changed (`git -C ../System-5 show --stat`), Ken pushes it, or tells Claude to:

    git -C ../System-5 push

`export.py` works from a commit (default `HEAD`), so commit in elf first; it never pushes. What it does:

- takes every file of that commit except `CLAUDE.md`, `docs/.removed-dups.txt` and `.github/workflows/website.yml`
  (the website is built and published from elf);
- puts the files in `overrides/` in place of the working ones: the Codespace set-up (`.devcontainer/` and
  `software/s5emu/CODESPACE.md`) without the private repository and Elf/OS v5;
- scans the result and stops on any finding: a file of the third-party folders moved to private-resources, a secret
  (private key, token, password), an email address, a phone number, a GPS position in a photo, a reserved-rights or
  do-not-distribute notice, a home-folder path (`/Users/<name>`), a file over 50 MB; inside zips and PDF streams too.
  Before the scan it takes the paths KiCad and Eagle write out of every text file: one into this repository becomes
  relative to it, any other starts at `~/` (2026-11-20). A finding checked by hand and kept is
  listed in `ALLOW` with the reason (two so far: CadSoft's address inside their own Eagle library, and six bytes of
  a gerber zip's packed data that read like an address: the scan reads a zip's own bytes as well as the files in it,
  so a chance run of packed bytes can look like text);
- makes the output folder hold exactly that tree. It refuses a folder it did not create itself.

## What was decided (Ken, 2026-11-15)

- The name `System-5`.
- Ken's designs and documents CC BY 4.0, his software MIT (`LICENSE.md`).
- HBIOS in, with Mike Riley's BIOS under his 2005 notice (`firmware/hbios/NOTICE.md`): free to share with the notice,
  not for commercial use without his permission.
- The old website copies (`docs/website-2005/`, `docs/website-older/`; their Yahoo visitor counter taken out), the
  2513 character fonts and all the Eagle libraries in.
- `CLAUDE.md` stays private.

What was moved out on 2026-11-15, and why: `reference/` (Mike Riley's ELF/OS and rcasm, the Spare Time Gizmos ELF2000,
Tiny BASIC, the tools, the datasheets), `firmware/elfos-install-rom/` and the two IC5 EPROM reads (Mike Riley's install
ROM), `firmware/system4-tiny-basic-rom/` (most likely Tom Pittman's Tiny BASIC), `software/disktool/` (Mike Riley's: his
2005 site handed out `disktool.tgz`) and `software/rcasm-mac-build/` (his rcasm). None of them carries a permission to
publish it. Mike Riley's 2004-05 BIOS does, which is why HBIOS could stay.
