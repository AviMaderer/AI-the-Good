# AI the Good

*Real deployments, positive impact!* Published under Future of Purpose.

AI the Good collects verified evidence that AI is already doing good for people: deployed tools and measured results from named institutions, each checked at the source. This repository is the publishing tool behind it: one page per edition, with ready-to-edit social posts and a roundup card.

Site: https://avimaderer.github.io/AI-the-Good/

## How an edition works

- An edition is named by its release day (Thursday, Israel time): `data/weeks/<DATE>.json`, published at `<site>/<DATE>/`.
- A scheduled task adds verified stories every day. Until release, the edition page is an unlinked preview.
- On release day the task picks the 3–4 card stories, writes five intro options and builds the page and `card.png`.
- Avi opens the preview, chooses or edits an intro and presses **Commit**. That writes `intro.final` to the edition file through the GitHub API; the **Build editions** workflow rebuilds the site, which releases the edition and writes the roundup post to `data/social/<DATE>.txt`.

The run rules (how stories are chosen, written and published) live in [`CONTENT_RULES.md`](CONTENT_RULES.md).

## Files

| File | What it controls |
|---|---|
| `CONTENT_RULES.md` | Run rules for the scheduled task |
| `data/config.json` | Name, byline, site URL, release weekday, timezone, opening lines |
| `data/sources.md` | Where to look for stories |
| `data/stories-log.csv`, `data/rejects.csv` | Stories already used, and stories checked and rejected |
| `data/dedications.csv` | Optional dedications (`start_date,end_date,text`); empty for now |
| `data/weeks/<DATE>.json` | An edition's stories and intro |
| `tools/build.py` | Builds an edition: `python tools/build.py data/weeks/<DATE>.json` (needs Playwright with Chromium) |

Generated (don't edit by hand): `<DATE>/` pages, images and `card.png`, `index.html`, `archive/`, `data/social/`.

## The Commit token

The Commit button needs a GitHub fine-grained personal access token with access to this repository only and the **Contents: Read and write** permission. Paste it once into the preview page; it is stored only in that browser's local storage.
