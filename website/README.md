# website/ — the System-5 project website

The project website is built from this repository's own documents with [MkDocs](https://www.mkdocs.org/) and the
[Material](https://squidfunk.github.io/mkdocs-material/) theme, the same way as the YACC1 and P8X sites. The
documents stay where they are; the site is a readable view of them, with navigation and search. **It is published at
<https://system5.cottageworker.com>**, since 2026-11-13.

| File | What |
|---|---|
| `home.md` | the visitor home page (the site's index) |
| `stage.py` | copies what the site uses into `stage/`, keeping repository paths so the links between documents work: the manual and its PDFs, the hardware notes, each KiCad revision's README and VIDEO-G's `kicad/README.md` (as `notes.md`), VIDEO-G's parts lists (`BOM.md`), the schematic PDFs, the photos and renders (resized) |
| `hooks.py` | MkDocs hook: links to repository files that are not on the site become plain text (the repository is private, so GitHub links would not open for visitors); each card's menu gets its KiCad revisions, named with their status from `hardware/FABRICATED.md` |
| `mkdocs.yml` | the site: navigation, theme, Markdown extensions |
| `mkdocs-publish.yml` | `mkdocs.yml` + the Google Analytics tag (G-X7P96DTCNE); only the published build carries it |
| `requirements.txt` | the Python packages, pinned |
| `build.sh` | stage + build (installs the packages into `venv/` on the first run, which needs the network) |

    website/build.sh            build into website/site/
    website/build.sh serve      ... and serve it at http://127.0.0.1:8767 (Ctrl-C stops it)
    website/build.sh publish    the build to publish (with Google Analytics)

`venv/`, `stage/` and `site/` are rebuilt each time and not committed.

**Never on the site:** third-party code and documents (not in this repository: since 2026-11-15 they are in the
private repository private-resources), `docs/website-2005/` and `docs/website-older/`
(the old 1802 site, kept as it is), `CLAUDE.md`, Eagle's backups.

**Publishing.** `.github/workflows/website.yml` runs on every push to `main` (or by hand: Actions -> website -> Run
workflow): it builds `website/build.sh publish` on GitHub's machine and deploys the result to GitHub Pages. **So every
push to `main` updates the public site.**

The site has been live since 2026-11-13 (checked 2026-11-14 with `gh variable list`, `gh api repos/ksr/elf/pages` and
`gh run list --workflow website.yml`):

- the repository variable `PAGES_DEPLOY` is `true` (set 2026-11-13; Settings -> Secrets and variables -> Actions ->
  Variables). The deploy job runs only while it is `true`;
- Pages is on (Settings -> Pages -> Source: GitHub Actions) with the custom domain `system5.cottageworker.com`: the
  domain is verified, its certificate approved, and HTTPS enforced;
- the CNAME record `system5` -> `ksr.github.io` is in place at Gandi;
- the first deployment was the run of 2026-11-13, started by hand.

To stop publishing, set `PAGES_DEPLOY` to anything but `true`: the workflow then only builds, which still proves on
every push that the site builds. That stops new deployments; what is already published stays up until Pages is turned
off in Settings -> Pages.

The repository is private and the site is public. GitHub Pages from a private repository needs a paid GitHub plan.
