"""Build one edition of AI the Good.

Stories are gathered every day into the upcoming edition, named by its release weekday
(release_weekday in data/config.json). The edition stays an unlinked preview until Avi commits
his intro on the preview page (intro.final in the edition file); the next build releases it.

Usage:  python tools/build.py data/weeks/YYYY-MM-DD.json      (YYYY-MM-DD = the edition's release date)

Reads   data/config.json, data/dedications.csv, the edition file
Writes  YYYY-MM-DD/index.html          the edition page (preview with the intro edit panel until released)
        YYYY-MM-DD/img/<key>.png       our branded image per story (only new ones are drawn)
        YYYY-MM-DD/card.png            the roundup card (1080x1350) from the stories with "card": true
        index.html                     redirects to the latest released edition
        archive/index.html             list of released editions
        data/social/YYYY-MM-DD.txt     the roundup post (released editions only)
        data/stories-log.csv           appends new stories (no duplicates)
        assets/og-card.png, assets/icon.png   (only if missing)
Needs   Python 3 + Playwright with Chromium (for the images).
"""
import asyncio, base64, csv, datetime as dt, hashlib, html, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
E = html.escape
TEAL, PALE, AMBER, SAGE = "#16302F", "#D4E4E0", "#E3A75E", "#A9C4BF"
BULLET_MAX = 78
LANGS = {"he": "Hebrew", "ar": "Arabic", "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese",
         "it": "Italian", "nl": "Dutch", "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "hi": "Hindi"}

SI = {"wa": "M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z", "fb": "M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z", "x": "M14.234 10.162 22.977 0h-2.072l-7.591 8.824L7.251 0H.258l9.168 13.343L.258 24H2.33l8.016-9.318L16.749 24h6.993zm-2.837 3.299-.929-1.329L3.076 1.56h3.182l5.965 8.532.929 1.329 7.754 11.09h-3.182z", "ms": "M12 0C5.24 0 0 4.952 0 11.64c0 3.499 1.434 6.521 3.769 8.61a.96.96 0 0 1 .323.683l.065 2.135a.96.96 0 0 0 1.347.85l2.381-1.053a.96.96 0 0 1 .641-.046A13 13 0 0 0 12 23.28c6.76 0 12-4.952 12-11.64S18.76 0 12 0m6.806 7.44c.522-.03.971.567.63 1.094l-4.178 6.457a.707.707 0 0 1-.977.208l-3.87-2.504a.44.44 0 0 0-.49.007l-4.363 3.01c-.637.438-1.415-.317-.995-.966l4.179-6.457a.706.706 0 0 1 .977-.21l3.87 2.505c.15.097.344.094.491-.007l4.362-3.008a.7.7 0 0 1 .364-.13"}  # Simple Icons (CC0)

def ico(path):
    return f'<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor" d="{path}"/></svg>'

def lang_note(code):
    return f"(Source article in {LANGS.get(code, code)}; your browser can translate it.)"

# ---------- inputs ----------
def load(edition_file):
    cfg = json.loads((ROOT / "data/config.json").read_text(encoding="utf-8"))
    path = pathlib.Path(edition_file)
    ed = json.loads(path.read_text(encoding="utf-8"))
    date = ed.get("edition") or ed.get("week")
    assert date == path.stem, f"edition date '{date}' does not match the file name {path.name}"
    release = dt.date.fromisoformat(date)
    weekday = cfg.get("release_weekday", "Thursday")
    assert release.strftime("%A") == weekday, f"{date} is a {release:%A}; editions are named by their {weekday}"
    ed["edition"] = date
    assert ed.get("stories"), "the edition has no stories"
    keys = set()
    for s in ed["stories"]:
        for k in ("key", "added", "tag", "teaser", "headline", "why", "texts", "source", "source_name"):
            assert s.get(k), f"story '{s.get('key')}' is missing '{k}'"
        assert s["key"] not in keys, f"duplicate key {s['key']}"
        keys.add(s["key"])
        if s.get("card"):
            b = (s.get("bullet") or "").strip()
            if not b:
                sys.exit(f"story '{s['key']}' is on the card but has no 'bullet'")
            if len(b) > BULLET_MAX:
                sys.exit(f"story '{s['key']}': bullet is {len(b)} characters (max {BULLET_MAX}). Shorten the text; do not shrink the font.")
        out = []
        for t in s["texts"]:
            t = t.rstrip()
            if cfg["hashtag"] not in t:
                lines = t.split("\n")
                if lines[-1].startswith("#"):
                    lines[-1] += " " + cfg["hashtag"]
                else:
                    lines += ["", cfg["hashtag"]]
                t = "\n".join(lines)
            code = s.get("source_lang")
            if code and code != "en" and lang_note(code) not in t:
                t += "\n\n" + lang_note(code)
            out.append(t)
        s["texts"] = out
    intro = ed.setdefault("intro", {})
    intro.setdefault("options", [])
    intro.setdefault("final", None)
    for o in intro["options"]:
        assert o.get("headline") and o.get("text"), "each intro option needs a headline and a text"
    if intro["final"] is not None:
        assert intro["final"].get("headline") and intro["final"].get("text"), "intro.final needs a headline and a text"
    n_card = sum(1 for s in ed["stories"] if s.get("card"))
    if n_card and not 3 <= n_card <= 4:
        print(f"WARNING: {n_card} card stories; the card should have 3 or 4.", file=sys.stderr)
    return cfg, ed, find_dedication(release)

def released(ed):
    f = (ed.get("intro") or {}).get("final")
    return bool(f and f.get("headline") and f.get("text"))

def find_dedication(release):
    """Dedication text for the edition released on `release`, or "".

    data/dedications.csv columns: start_date,end_date,text (YYYY-MM-DD). Dates are inclusive;
    end_date may be empty for a single day. A row applies if its period overlaps the seven days
    ending on the release date. If several rows apply, the shortest period wins; ties go to the later row.
    """
    start_of = release - dt.timedelta(days=6)
    best, best_len = "", None
    p = ROOT / "data/dedications.csv"
    if not p.exists():
        return ""
    with open(p, encoding="utf-8") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            text = (row.get("text") or "").strip()
            start = (row.get("start_date") or row.get("date") or "").strip()
            end = (row.get("end_date") or "").strip() or start
            if not text or not start:
                continue
            try:
                a, b = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
            except ValueError:
                sys.exit(f"dedications.csv line {n}: dates must be YYYY-MM-DD (got '{start}', '{end}')")
            if b < a:
                sys.exit(f"dedications.csv line {n}: end_date {end} is before start_date {start}")
            if a <= release and b >= start_of and (best_len is None or (b - a).days <= best_len):
                best, best_len = text, (b - a).days
    return best

def nice(d):
    d = dt.date.fromisoformat(d) if isinstance(d, str) else d
    return f"{d.day} {d.strftime('%B %Y')}"

def paras(text):
    return "".join(f"<p>{E(p.strip())}</p>" for p in text.split("\n\n") if p.strip())

def social_post(cfg, ed):
    f = ed["intro"]["final"]
    return f"{f['headline'].strip()}\n\n{f['text'].strip()}\n\n{cfg['site_url']}{ed['edition']}/\n"

# ---------- brand pieces ----------
def mark(size, bg=AMBER, fg=TEAL):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 48 48" aria-hidden="true">'
            f'<rect width="48" height="48" rx="12" fill="{bg}"/>'
            f'<path d="M24 8C25.6 18.6 29.4 22.4 40 24C29.4 25.6 25.6 29.4 24 40C22.4 29.4 18.6 25.6 8 24C18.6 22.4 22.4 18.6 24 8Z" fill="{fg}"/>'
            f'<circle cx="36" cy="12" r="3" fill="{fg}"/></svg>')

def font_css(prefix, embed=False):
    def src(file):
        if embed:
            return "data:font/woff2;base64," + base64.b64encode((ROOT / "assets/fonts" / file).read_bytes()).decode()
        return f"{prefix}assets/fonts/{file}"
    f = lambda fam, w, file: (f"@font-face{{font-family:'{fam}';font-weight:{w};font-display:swap;"
                              f"src:url({src(file)}) format('woff2')}}")
    return "\n".join([f("Rubik", 500, "rubik-latin-500-normal.woff2"), f("Rubik", 700, "rubik-latin-700-normal.woff2"),
                      f("Assistant", 400, "assistant-latin-400-normal.woff2"), f("Assistant", 700, "assistant-latin-700-normal.woff2")])

# ---------- images (Playwright) ----------
BG = (f"background:{TEAL};background-image:radial-gradient(rgba(212,228,224,.07) 2.5px, transparent 2.5px);"
      "background-size:44px 44px")

def story_image_html(cfg, s):
    return f'''<html><head><style>{font_css("", embed=True)}
body{{margin:0;width:1080px;height:1080px;overflow:hidden;font-family:Rubik}}
.c{{width:1080px;height:1080px;box-sizing:border-box;padding:84px;display:flex;flex-direction:column;{BG}}}
.b{{display:flex;align-items:center;gap:18px;font:500 30px/1 Rubik;letter-spacing:.12em;color:{SAGE}}}
.t{{margin-top:auto;font:500 30px/1 Rubik;letter-spacing:.1em;text-transform:uppercase;color:{AMBER}}}
h1{{margin:22px 0 0;font:700 86px/1.06 Rubik;color:{PALE};letter-spacing:-.015em;text-wrap:balance}}
.r{{margin-top:44px;height:8px;width:140px;background:{AMBER};border-radius:4px}}
</style></head><body><div class="c"><div class="b">{mark(56)}{E(cfg["site_name"]).upper()}</div>
<div class="t">{E(s["tag"])}</div><h1>{E(s["headline"])}</h1><div class="r"></div></div></body></html>'''

def bullet_html(text):
    i = text.find(",")
    if i < 0:
        return f"<b>{E(text)}</b>"
    return f"<b>{E(text[:i])}</b>{E(text[i:])}"

def card_html(cfg, ed):
    """The roundup card (1080x1350). Fixed design, specified in CONTENT_RULES.md section 5: keep the two in step."""
    d = dt.date.fromisoformat(ed["edition"])
    name = cfg["site_name"]
    title = E(name[:-4]) + "<mark>Good</mark>" if name.endswith("Good") else E(name)
    items = "".join(f"<li>{bullet_html(s['bullet'].strip())}</li>" for s in ed["stories"] if s.get("card"))
    return f'''<html><head><style>{font_css("", embed=True)}
body{{margin:0;width:1080px;height:1350px;overflow:hidden}}
.c{{width:1080px;height:1350px;box-sizing:border-box;padding:84px 88px 76px;display:flex;flex-direction:column;background:{TEAL}}}
.hd{{display:flex;justify-content:space-between;align-items:center;font:500 26px/1 Rubik;letter-spacing:.16em;color:{SAGE}}}
.hr{{height:2px;background:{SAGE};opacity:.35;margin:30px 0 0}}
h1{{margin:64px 0 0;font:700 132px/1 Rubik;letter-spacing:-.025em;color:{PALE}}}
h1 mark{{background:{AMBER};color:{TEAL};padding:0 .14em;border-radius:12px;-webkit-box-decoration-break:clone}}
.by{{margin:30px 0 0;font:500 40px/1.2 Rubik;color:{SAGE}}}
.bar{{margin-top:48px;height:8px;width:140px;background:{AMBER};border-radius:4px}}
ul{{list-style:none;margin:56px 0 0;padding:0;display:flex;flex-direction:column;gap:36px}}
li{{position:relative;padding-left:44px;font:400 42px/1.28 Assistant;color:{PALE}}}
li::before{{content:"";position:absolute;left:0;top:.42em;width:18px;height:18px;border-radius:50%;background:{AMBER}}}
li b{{font-weight:700;color:#fff}}
.ft{{margin-top:auto;padding-top:30px;border-top:2px solid rgba(169,196,191,.35);font:500 30px/1 Rubik;letter-spacing:.03em;color:{SAGE}}}
</style></head><body><div class="c">
<div class="hd"><span>{E(cfg.get("publisher", "Future of Purpose")).upper()}</span><span>{E(d.strftime("%B").upper())} {d.day}, {d.year}</span></div>
<div class="hr"></div>
<h1>{title}</h1>
<p class="by">{E(cfg["byline"])}</p>
<div class="bar"></div>
<ul>{items}</ul>
<div class="ft">{E(cfg.get("publisher_url", "futureofpurpose.substack.com"))}</div>
</div></body></html>'''

def og_html(cfg):
    return f'''<html><head><style>{font_css("", embed=True)}
body{{margin:0;width:1200px;height:630px;overflow:hidden}}
.c{{width:1200px;height:630px;box-sizing:border-box;padding:90px;display:flex;flex-direction:column;justify-content:center;gap:28px;{BG}}}
h1{{margin:0;font:700 96px/1 Rubik;color:{PALE};letter-spacing:-.02em}} p{{margin:0;font:500 40px/1.2 Rubik;color:{AMBER}}}
</style></head><body><div class="c">{mark(110)}<h1>{E(cfg["site_name"])}</h1><p>{E(cfg["byline"])}</p></div></body></html>'''

async def render(jobs):
    if not jobs:
        return
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for html_src, path, w, h in jobs:
            pg = await b.new_page(viewport={"width": w, "height": h})
            await pg.set_content(html_src); await pg.wait_for_timeout(300)
            path.parent.mkdir(parents=True, exist_ok=True)
            await pg.screenshot(path=str(path)); await pg.close()
        await b.close()

# ---------- page ----------
PAGE_CSS = """
:root{--accent:#1F5E57;--amber:#E3A75E;--bg:#EEF3F1;--paper:#FFFFFF;--ink:#16302F;--muted:#4F6662;--line:#D3E0DC;--btn-fg:#FFFFFF;--soft:#E1ECE9;--ok:#1E7A4C;--err:#B3261E;
 --f-display:'Rubik','Segoe UI',system-ui,sans-serif;--f-body:'Assistant','Segoe UI',system-ui,sans-serif;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--accent:#8FD0C4;--amber:#E3A75E;--bg:#0F2221;--paper:#16302F;--ink:#E6F0EE;--muted:#A9C4BF;--line:#2A4744;--btn-fg:#0F2221;--soft:#1E3D3A;--ok:#6FD3A0;--err:#FF8A80;color-scheme:dark}}
:root[data-theme="dark"]{--accent:#8FD0C4;--amber:#E3A75E;--bg:#0F2221;--paper:#16302F;--ink:#E6F0EE;--muted:#A9C4BF;--line:#2A4744;--btn-fg:#0F2221;--soft:#1E3D3A;--ok:#6FD3A0;--err:#FF8A80;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:400 18px/1.5 var(--f-body);padding-inline:16px;padding-block:max(20px,env(safe-area-inset-top)) 48px}
.wrap{max-width:560px;margin:0 auto;display:grid;gap:22px;min-width:0}
header{display:grid;gap:6px;padding-top:8px}
.brand{display:flex;align-items:center;gap:10px;font:500 14px/1 var(--f-display);letter-spacing:.14em;color:var(--accent);text-transform:uppercase;text-decoration:none}
header h1{margin:6px 0 0;font:700 clamp(30px,8vw,40px)/1.05 var(--f-display);letter-spacing:-.015em;text-wrap:balance}
.byline{margin:0;color:var(--muted);font:500 17px/1.3 var(--f-display)}
.date{margin:0;color:var(--muted);font-size:16px}
.ded{margin:6px 0 0;padding:12px 16px;border-radius:10px;background:var(--paper);border:1px solid var(--line);font-size:17px;text-align:center;line-height:1.45}
.ded b{font-family:var(--f-display);font-weight:500}
.ded .name{display:block;font-family:var(--f-display);font-weight:700}
.intro{background:var(--paper);border:1px solid var(--line);border-left:5px solid var(--amber);border-radius:12px;padding:16px 18px;display:grid;gap:8px}
.intro-k{margin:0;font:500 12px/1 var(--f-display);letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.intro-h{margin:0;font:700 22px/1.2 var(--f-display);letter-spacing:.01em;text-transform:uppercase;text-wrap:balance}
.intro-t{display:grid;gap:10px}.intro-t p{margin:0}
.heads{margin:10px 0 0;border:1px solid var(--line);border-radius:10px;background:var(--paper);padding:0 16px}
.heads summary{cursor:pointer;padding:12px 0;font:500 15px/1.2 var(--f-display);color:var(--accent)}
.heads ul{margin:0 0 14px;padding-left:20px;display:grid;gap:6px;font-size:16px}
.heads a{color:var(--ink)}
.sec{margin:8px 0 0;font:500 13px/1 var(--f-display);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.list{display:grid;gap:14px}
.story{background:var(--paper);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.story>summary{list-style:none;cursor:pointer;padding:16px 18px;display:grid;gap:6px}
.story>summary::-webkit-details-marker{display:none}
.story[open]>summary{padding-bottom:4px}
.top{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font:500 12px/1 var(--f-display);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.badge{padding:4px 7px;border-radius:999px;letter-spacing:.04em}
.badge.card{color:var(--ink);background:var(--amber);color:#16302F}
.badge.done{color:var(--muted);border:1px solid var(--line)}
.preview-note{margin:0;padding:10px 14px;border-radius:10px;background:var(--amber);color:#16302F;font:500 15px/1.35 var(--f-display)}
.story h2{margin:0;font:700 21px/1.2 var(--f-display);letter-spacing:-.01em;text-wrap:balance}
.why{margin:0;color:var(--muted);font-size:16px}
.more-cue{font:500 14px/1 var(--f-display);color:var(--accent)}
.story[open] .more-cue{display:none}
.body{padding:8px 18px 20px;display:grid;gap:12px;min-width:0}
.preview{display:block;text-decoration:none;color:inherit;background:var(--soft);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.og{display:block;width:100%;max-width:100%;aspect-ratio:1.91;object-fit:cover;background:var(--line)}
.pmeta{display:grid;gap:4px;padding:10px 14px 12px}
.site{font:500 12px/1 var(--f-display);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.ogt{font:500 15px/1.3 var(--f-display);color:var(--ink)}
.tip{margin:0;font-size:15px;color:var(--muted)}
.post{width:100%;resize:vertical;font:400 17px/1.5 var(--f-body);color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:12px 14px;min-height:240px}
.post:focus-visible,.btn:focus-visible,.net:focus-visible,.tool:focus-visible,summary:focus-visible,.field:focus-visible{outline:3px solid var(--amber);outline-offset:2px}
.actions{display:flex;flex-wrap:wrap;gap:8px}
.btn{flex:1 1 auto;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;border:1px solid var(--accent);background:transparent;color:var(--accent);border-radius:10px;padding:12px 14px;font:500 15px/1 var(--f-display);cursor:pointer;min-height:46px}
.btn.primary{background:var(--accent);color:var(--btn-fg);flex-basis:100%}
.btn:disabled{opacity:.55;cursor:default}
.share-h{margin:6px 0 0;font:500 13px/1 var(--f-display);letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.share-note{margin:0;font-size:14px;color:var(--muted)}
.nets{display:flex;flex-wrap:nowrap;gap:6px}
.net{display:flex;align-items:center;justify-content:center;flex:1 1 0;min-width:0;max-width:44px;aspect-ratio:1;border-radius:50%;border:0;padding:0;cursor:pointer;text-decoration:none;color:#fff}
.net.wa{background:#25D366}.net.fb{background:#0866FF}.net.ms{background:#0866FF}.net.li{background:#0A66C2}.net.sms{background:#34C759}
.net.x{background:var(--ink);color:var(--paper)}
.net .in{font:700 19px/1 var(--f-display);letter-spacing:-.02em}
.net[hidden]{display:none}
.net.more{background:transparent;color:var(--accent);border:1.5px solid var(--accent)}
.hint{margin:0;min-height:1.2em;font-size:15px;color:var(--accent)}
.ours{border:1px solid var(--line);border-radius:10px;padding:14px;display:grid;gap:10px}
.ours[hidden]{display:none}
.edit-h{margin-top:6px;font:700 16px/1.3 var(--f-display);color:var(--ink)}
.tools{display:flex;justify-content:flex-end;flex-wrap:wrap;gap:8px;margin-top:-4px}
.tool{border:0;background:var(--soft);color:var(--accent);font:500 14px/1 var(--f-display);padding:9px 12px;border-radius:999px;cursor:pointer}
.tool[aria-expanded="true"]{background:var(--accent);color:var(--btn-fg)}
.ours p{margin:0;font-size:15px;color:var(--muted)}
.art{display:block;width:100%;height:auto;aspect-ratio:1;max-width:100%;border-radius:8px}
.src{margin:0;font-size:15px;color:var(--muted);border-top:1px solid var(--line);padding-top:12px}
.src a{color:var(--ink)}
.lang{font:500 12px/1 var(--f-display);padding:3px 6px;border-radius:6px;background:var(--soft);color:var(--accent);margin-left:4px}
.panel{background:var(--paper);border:2px solid var(--accent);border-radius:14px;padding:16px;display:grid;gap:12px;min-width:0}
.panel[hidden],.panel [hidden]{display:none !important}
.panel h2{margin:0;font:700 19px/1.2 var(--f-display)}
.panel .grp{display:grid;gap:10px;min-width:0}
.flabel{font:500 14px/1 var(--f-display);color:var(--muted);display:flex;justify-content:space-between;gap:8px}
.field{width:100%;min-width:0;font:400 17px/1.45 var(--f-body);color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:11px 13px}
input.field{font-size:17px}
#in-h{font:700 17px/1.3 var(--f-display);text-transform:uppercase}
textarea.field{resize:vertical;min-height:170px}
.nav{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:8px}
.nav .btn{flex:none;min-width:0;padding:10px 12px}
.pos{text-align:center;font:500 14px/1.25 var(--f-display);color:var(--muted)}
.pos b{display:block;color:var(--ink);font-weight:500;text-transform:capitalize}
.msg{margin:0;font-size:16px;line-height:1.4}
.msg.err{color:var(--err)}.msg.ok{color:var(--ok)}
.linkbtn{justify-self:start;border:0;background:none;padding:6px 0;color:var(--muted);font:400 15px/1 var(--f-body);text-decoration:underline;cursor:pointer}
footer{display:grid;gap:10px;color:var(--muted);font-size:15px}
footer a{color:var(--ink)}
"""

PAGE_JS = r"""
const enc = encodeURIComponent;
const store = { get(){ try { return new Set(JSON.parse(localStorage.getItem('aitg-shared') || '[]')); } catch { return new Set(); } },
                add(k){ try { const s = this.get(); s.add(k); localStorage.setItem('aitg-shared', JSON.stringify([...s])); } catch {} } };
const shared = store.get();
const rand = a => a.map(v => [Math.random(), v]).sort((x, y) => x[0] - y[0]).map(x => x[1]);
const opOrder = rand(OPENERS.map((_, i) => i));
const cards = [...document.querySelectorAll('.story')];
document.querySelectorAll('.jump').forEach(a => a.addEventListener('click', e => {
  const c = document.getElementById(a.getAttribute('href').slice(1)); if (!c) return;
  e.preventDefault(); c.open = true; c.scrollIntoView({ behavior: 'smooth', block: 'start' });
}));

cards.forEach((card, idx) => {
  const key = card.dataset.key, m = META[key];
  const img = card.querySelector('.art'), ta = card.querySelector('.post'), hint = card.querySelector('.hint');
  const og = card.querySelector('.og');
  const say = t => { hint.textContent = t; clearTimeout(card._t); card._t = setTimeout(() => hint.textContent = '', 4500); };
  const fallback = () => { og.onerror = null; og.src = og.dataset.fallback; og.style.aspectRatio = '1'; };
  if (!og.getAttribute('src')) fallback(); else { og.onerror = fallback; if (og.complete && og.naturalWidth === 0) fallback(); }
  if (shared.has(key)) card.querySelector('.top').insertAdjacentHTML('beforeend', '<span class="badge done">Shared</span>');
  const markShared = () => { if (!shared.has(key)) { shared.add(key); store.add(key); card.querySelector('.top').insertAdjacentHTML('beforeend', '<span class="badge done">Shared</span>'); } };
  let oi = idx, vi = Math.floor(Math.random() * m.texts.length);
  const opener = () => OPENERS[opOrder[oi % OPENERS.length]];
  const compose = () => opener() + '\n\n' + m.texts[vi % m.texts.length];
  let last = compose(); ta.value = last;
  const links = () => {
    const t = ta.value.trim();
    card.querySelector('.wa').href = 'https://wa.me/?text=' + enc(t + '\n\n' + m.source);
    card.querySelector('.x').href = 'https://twitter.com/intent/tweet?text=' + enc(m.headline) + '&url=' + enc(m.source);
    card.querySelector('.fb').href = 'https://www.facebook.com/sharer/sharer.php?u=' + enc(m.source);
    card.querySelector('.li').href = 'https://www.linkedin.com/sharing/share-offsite/?url=' + enc(m.source);
    card.querySelector('.sms').href = 'sms:?&body=' + enc(t + '\n\n' + m.source);
    card.querySelector('.ms').href = 'fb-messenger://share?link=' + enc(m.source);
  };
  // Text messages only make sense on phones.
  if (!matchMedia('(pointer: coarse)').matches) { card.querySelector('.sms').hidden = true; card.querySelector('.ms').hidden = true; }
  card.querySelector('.swap').addEventListener('click', () => {
    const oldOpener = opener(); oi += 1; vi += 1;
    if (ta.value === last) { last = compose(); ta.value = last; say('New wording. Edit it any way you like.'); }
    else if (ta.value.startsWith(oldOpener)) { ta.value = opener() + ta.value.slice(oldOpener.length); say('You edited the text, so only the opening line changed.'); }
    else { ta.value = opener() + '\n\n' + ta.value; say('Added a new opening line above your text.'); }
    links();
  });
  links(); ta.addEventListener('input', links);
  const file = async () => new File([await (await fetch(img.src)).blob()], `ai-the-good-${key}.png`, { type: 'image/png' });
  const copy = async (txt = ta.value) => {
    try { await navigator.clipboard.writeText(txt); return true; }
    catch { ta.select(); try { return document.execCommand('copy'); } catch { return false; } }
  };
  const full = () => ta.value.trim() + '\n\n' + m.source;
  // Every share button copies the post as well, so it can be pasted if the app doesn't fill it in.
  const nets = {
    wa: ['full', 'WhatsApp is opening with your post filled in. Pick a chat, group or Status.'],
    x:  ['full', 'X is opening. Your post is also copied, so you can paste the full text.'],
    sms:['full', 'Your messages app is opening with the post filled in.'],
    fb: ['text', 'Copied. When Facebook opens, tap the post box and paste.'],
    li: ['text', 'Copied. When LinkedIn opens, tap the post box and paste.'],
    ms: ['text', 'Copied. Pick a chat in Messenger, then paste the text above the link.'],
  };
  Object.entries(nets).forEach(([cls, [what, msg]]) => card.querySelector('.' + cls).addEventListener('click', () => {
    markShared(); copy(what === 'full' ? full() : ta.value.trim()); say(msg);
  }));
  card.querySelector('.more').addEventListener('click', async () => {
    markShared();
    try { if (navigator.share) { await navigator.share({ text: ta.value.trim(), url: m.source }); return; } }
    catch (e) { if (e && e.name === 'AbortError') return; }
    say(await copy(full()) ? 'Copied with the link. Paste it anywhere you like.' : 'Select the text and copy it.');
  });
  const tog = card.querySelector('.img-toggle'), ours = card.querySelector('.ours');
  tog.addEventListener('click', () => {
    ours.hidden = !ours.hidden; tog.setAttribute('aria-expanded', String(!ours.hidden));
    tog.innerHTML = ours.hidden ? '&#128444; Use our image' : '&#10005; Hide image';
  });
  card.querySelector('.dl').addEventListener('click', async () => {
    markShared();
    const f = await file(), a = document.createElement('a');
    a.href = URL.createObjectURL(f); a.download = f.name; document.body.appendChild(a); a.click(); a.remove();
    say('Image saved. On a phone you can also press and hold the image.');
  });
  card.querySelector('.share-img').addEventListener('click', async () => {
    markShared();
    const text = ta.value.trim() + '\n\n' + m.source;
    try {
      const f = await file();
      if (navigator.canShare && navigator.canShare({ files: [f] })) { await navigator.share({ files: [f], text }); return; }
      if (navigator.share) { await navigator.share({ text }); return; }
    } catch (e) { if (e && e.name === 'AbortError') return; }
    await copy(); say('Sharing works on phones. Text copied: download the image and paste the text.');
  });
});
"""

# Intro edit panel: unreleased previews only. The token lives only in this browser's localStorage.
PANEL_JS = r"""
(() => {
  const $ = id => document.getElementById(id);
  const TOKEN_KEY = 'aitg-gh-token', DRAFT_KEY = 'aitg-draft-' + ED.date;
  const ls = { get(k){ try { return localStorage.getItem(k); } catch { return null; } },
               set(k, v){ try { localStorage.setItem(k, v); return true; } catch { return false; } },
               del(k){ try { localStorage.removeItem(k); } catch {} } };
  const opts = ED.options.map(o => ({ angle: o.angle || '', headline: o.headline, text: o.text }));
  let i = 0;
  try { const d = JSON.parse(ls.get(DRAFT_KEY) || 'null'); if (d && d.opts && d.opts.length === opts.length) { d.opts.forEach((o, n) => Object.assign(opts[n], { headline: o.headline, text: o.text })); i = Math.min(d.i || 0, opts.length - 1); } } catch {}
  const tok = $('tok'), edit = $('edit'), done = $('done');
  const inH = $('in-h'), inT = $('in-t'), msg = $('msg'), tokMsg = $('tok-msg');
  const say = (el, text, kind) => { el.textContent = text; el.className = 'msg' + (kind ? ' ' + kind : ''); };
  const words = t => (t.trim().match(/\S+/g) || []).length;

  // Live preview of the intro block above the stories.
  const showIntro = () => {
    $('intro-h').textContent = inH.value.trim().toUpperCase();
    const t = $('intro-t'); t.textContent = '';
    inT.value.split(/\n\s*\n/).filter(p => p.trim()).forEach(p => { const e = document.createElement('p'); e.textContent = p.trim(); t.appendChild(e); });
  };
  const draw = () => {
    const o = opts[i];
    $('pos').innerHTML = ''; $('pos').append('Option ' + (i + 1) + ' of ' + opts.length);
    const b = document.createElement('b'); b.textContent = o.angle.replace(/-/g, ' '); $('pos').appendChild(b);
    inH.value = o.headline; inT.value = o.text; count(); showIntro();
  };
  const count = () => { $('count').textContent = words(inT.value) + ' words'; };
  const keep = () => { opts[i].headline = inH.value; opts[i].text = inT.value; ls.set(DRAFT_KEY, JSON.stringify({ i, opts })); };
  inH.addEventListener('input', () => { keep(); showIntro(); });
  inT.addEventListener('input', () => { keep(); count(); showIntro(); });
  $('prev').addEventListener('click', () => { i = (i - 1 + opts.length) % opts.length; keep(); draw(); });
  $('next').addEventListener('click', () => { i = (i + 1) % opts.length; keep(); draw(); });

  const mode = (which, note, kind) => {
    tok.hidden = which !== 'tok'; edit.hidden = which !== 'edit'; done.hidden = which !== 'done';
    if (which === 'tok') { say(tokMsg, note || 'Paste your GitHub token to choose and commit the intro. It is kept only in this browser.', kind); $('tok-in').value = ''; }
  };

  // ---- GitHub contents API ----
  const API = 'https://api.github.com/repos/' + ED.repo + '/contents/data/weeks/' + ED.date + '.json';
  const b64decode = b => new TextDecoder().decode(Uint8Array.from(atob(b.replace(/\s/g, '')), c => c.charCodeAt(0)));
  const b64encode = s => { const u = new TextEncoder().encode(s); let bin = ''; for (let k = 0; k < u.length; k += 0x8000) bin += String.fromCharCode(...u.subarray(k, k + 0x8000)); return btoa(bin); };
  class GHError extends Error { constructor(status, text){ super(text); this.status = status; } }
  const gh = async (method, body) => {
    const token = ls.get(TOKEN_KEY);
    if (!token) throw new GHError(401, 'no token');
    let r;
    try {
      r = await fetch(API + (method === 'GET' ? '?ref=' + enc(ED.branch) : ''), {
        method, cache: 'no-store',
        headers: { 'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
                   ...(body ? { 'Content-Type': 'application/json' } : {}) },
        body: body ? JSON.stringify(body) : undefined });
    } catch { throw new GHError(0, 'network'); }
    let j = {}; try { j = await r.json(); } catch {}
    if (!r.ok) throw new GHError(r.status, j.message || r.statusText);
    return j;
  };
  const explain = e => {
    if (e.status === 401) { ls.del(TOKEN_KEY); return ['tok', e.message === 'no token' ? '' : 'GitHub rejected the token: it has expired or been revoked. Paste a new one.', 'err']; }
    if (e.status === 403) return ['tok', 'GitHub refused (' + e.message + '). The token needs Contents: Read and write on ' + ED.repo + '. Paste a token that has it.', 'err'];
    if (e.status === 404) return ['tok', 'GitHub could not find data/weeks/' + ED.date + '.json in ' + ED.repo + '. Make sure the token has access to that repository, then paste it again.', 'err'];
    if (e.status === 0) return ['edit', 'Could not reach GitHub. Check your connection and try again.', 'err'];
    return ['edit', 'GitHub returned an error (' + e.status + ': ' + e.message + '). Nothing was committed. Try again.', 'err'];
  };
  const fail = e => { const [w, text, kind] = explain(e); if (w === 'tok') mode('tok', text, kind); else say(msg, text, kind); };

  $('tok-save').addEventListener('click', async () => {
    const v = $('tok-in').value.trim();
    if (!v) { say(tokMsg, 'Paste the token first.', 'err'); return; }
    if (!ls.set(TOKEN_KEY, v)) { say(tokMsg, 'This browser is blocking local storage, so the token cannot be kept. Allow site data for this page and try again.', 'err'); return; }
    say(tokMsg, 'Checking the token with GitHub…');
    try { await gh('GET'); mode('edit'); draw(); say(msg, 'Token saved in this browser.', 'ok'); }
    catch (e) { fail(e); }
  });
  $('tok-in').addEventListener('keydown', e => { if (e.key === 'Enter') $('tok-save').click(); });
  $('forget').addEventListener('click', () => { ls.del(TOKEN_KEY); mode('tok', 'Token removed from this browser.'); });

  $('commit').addEventListener('click', async () => {
    const headline = inH.value.trim().toUpperCase(), text = inT.value.trim();
    if (!headline || !text) { say(msg, 'The headline and the text both need something in them.', 'err'); return; }
    const btn = $('commit'); btn.disabled = true; say(msg, 'Committing to GitHub…');
    const final = { headline, text, angle: opts[i].angle, committed_at: new Date().toISOString() };
    try {
      let res;
      for (let attempt = 0; ; attempt++) {
        const cur = await gh('GET');
        const data = JSON.parse(b64decode(cur.content));
        data.intro = data.intro || {}; data.intro.final = final;
        try {
          res = await gh('PUT', { message: 'Intro ' + ED.date + ': release', branch: ED.branch, sha: cur.sha,
                                  content: b64encode(JSON.stringify(data, null, 2) + '\n') });
          break;
        } catch (e) { if ((e.status === 409 || e.status === 422) && attempt === 0) continue; throw e; }
      }
      ls.del(DRAFT_KEY);
      const post = headline + '\n\n' + text + '\n\n' + ED.url + '\n';
      $('post').value = post;
      const link = $('commit-link'); if (res && res.commit && res.commit.html_url) { link.href = res.commit.html_url; link.hidden = false; }
      mode('done');
    } catch (e) { fail(e); }
    finally { btn.disabled = false; }
  });
  $('copy-post').addEventListener('click', async () => {
    const t = $('post'); let ok = false;
    try { await navigator.clipboard.writeText(t.value); ok = true; } catch { t.select(); try { ok = document.execCommand('copy'); } catch {} }
    say($('done-msg'), ok ? 'Post copied. Paste it into Facebook or LinkedIn with the card.' : 'Select the text and copy it.', ok ? 'ok' : 'err');
  });

  $('panel').hidden = false;
  if (ls.get(TOKEN_KEY)) { mode('edit'); draw(); } else { mode('tok'); showIntro(); draw(); }
})();
"""

def story_html(s, preview):
    k = E(s["key"])
    code = s.get("source_lang")
    lang = f'<span class="lang">{E(LANGS.get(code, code))}</span>' if code and code != "en" else ""
    card = '<span class="badge card">On card</span>' if preview and s.get("card") else ""
    return f'''
<details class="story" id="{k}" data-key="{k}">
  <summary>
    <span class="top">{E(s['tag'])}{card}</span>
    <h2>{E(s['headline'])}</h2>
    <p class="why">{E(s['why'])}</p>
    <span class="more-cue">Open to share &#8250;</span>
  </summary>
  <div class="body">
    <a class="preview" href="{E(s['source'])}" target="_blank" rel="noopener">
      <img class="og" src="{E(s.get('og_image', ''))}" alt="" loading="lazy" referrerpolicy="no-referrer" data-fallback="img/{k}.png">
      <span class="pmeta"><span class="site">{E(s.get('site', ''))}{lang}</span><span class="ogt">{E(s.get('og_title') or s['headline'])}</span></span>
    </a>
    <label class="edit-h" for="t-{k}">&#9998; Your post: edit it any way you like</label>
    <textarea id="t-{k}" class="post" rows="11" spellcheck="true"></textarea>
    <div class="tools">
      <button type="button" class="tool swap">&#8635; New wording</button>
      <button type="button" class="tool img-toggle" aria-expanded="false" aria-controls="img-{k}">&#128444; Use our image</button>
    </div>
    <div class="ours" id="img-{k}" hidden>
      <p>For Instagram, a story or a photo post.</p>
      <img class="art" src="img/{k}.png" alt="{E(s['headline'])}" width="1080" height="1080" loading="lazy">
      <div class="actions">
        <button type="button" class="btn dl">Download image</button>
        <button type="button" class="btn share-img">Share image + text</button>
      </div>
    </div>
    <p class="share-h">Share to</p>
    <div class="nets" aria-label="Share to">
      <a class="net wa" target="_blank" rel="noopener" aria-label="WhatsApp" title="WhatsApp">{ico(SI["wa"])}</a>
      <a class="net fb" target="_blank" rel="noopener" aria-label="Facebook" title="Facebook">{ico(SI["fb"])}</a>
      <a class="net ms" aria-label="Messenger" title="Messenger">{ico(SI["ms"])}</a>
      <a class="net x" target="_blank" rel="noopener" aria-label="X" title="X">{ico(SI["x"])}</a>
      <a class="net li" target="_blank" rel="noopener" aria-label="LinkedIn" title="LinkedIn"><span class="in">in</span></a>
      <a class="net sms" aria-label="Text message" title="Text message"><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor" d="M12 3C6.5 3 2 6.6 2 11c0 2.4 1.3 4.6 3.5 6.1L4.6 21l4.3-2.4c1 .3 2 .4 3.1.4 5.5 0 10-3.6 10-8s-4.5-8-10-8z"/></svg></a>
      <button type="button" class="net more" aria-label="More apps" title="More apps"><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><circle cx="6" cy="12" r="2.2" fill="currentColor"/><circle cx="12" cy="12" r="2.2" fill="currentColor"/><circle cx="18" cy="12" r="2.2" fill="currentColor"/></svg></button>
    </div>
    <p class="share-note">Tap an app. Your post is copied too, so if it isn't filled in when the app opens, just paste it.</p>
    <p class="hint" aria-live="polite"></p>
    <p class="src">Source: <a href="{E(s['source'])}" target="_blank" rel="noopener">{E(s['source_name'])}</a>{lang}</p>
  </div>
</details>'''

def dedication_html(cfg, ded):
    if ded:
        return f'<p class="ded">This edition is dedicated<span class="name">{E(ded)}</span></p>'
    if cfg.get("dedication_contact"):
        return (f'<p class="ded"><b>Dedicate an edition</b> in honor or in memory of someone you love. '
                f'Contact: {E(cfg["dedication_contact"])}</p>')
    return ""

def intro_html(ed, preview):
    intro = ed["intro"]
    if intro["final"]:
        o, label = intro["final"], ""
    elif preview and intro["options"]:
        o, label = intro["options"][0], '<p class="intro-k">Draft intro: not committed yet</p>'
    else:
        return ""
    return (f'<section class="intro" aria-label="Intro">{label}<h2 class="intro-h" id="intro-h">{E(o["headline"].upper())}</h2>'
            f'<div class="intro-t" id="intro-t">{paras(o["text"])}</div></section>')

PANEL_HTML = """
<section class="panel" id="panel" aria-labelledby="panel-h" hidden>
  <h2 id="panel-h">Your intro</h2>
  <div class="grp" id="tok">
    <p class="msg" id="tok-msg" aria-live="polite"></p>
    <label class="flabel" for="tok-in">GitHub token</label>
    <input class="field" id="tok-in" type="password" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="github_pat_…">
    <button type="button" class="btn primary" id="tok-save">Paste token</button>
  </div>
  <div class="grp" id="edit">
    <div class="nav">
      <button type="button" class="btn" id="prev" aria-label="Previous option">&#8249; Previous</button>
      <span class="pos" id="pos" aria-live="polite"></span>
      <button type="button" class="btn" id="next" aria-label="Next option">Next &#8250;</button>
    </div>
    <label class="flabel" for="in-h"><span>Headline</span><span>saved in capitals</span></label>
    <input class="field" id="in-h" type="text" autocomplete="off">
    <label class="flabel" for="in-t"><span>Text</span><span id="count"></span></label>
    <textarea class="field" id="in-t" rows="8" spellcheck="true"></textarea>
    <button type="button" class="btn primary" id="commit">Commit intro and release</button>
    <p class="msg" id="msg" aria-live="polite"></p>
    <button type="button" class="linkbtn" id="forget">Forget token on this device</button>
  </div>
  <div class="grp" id="done">
    <p class="msg ok">Committed. GitHub is rebuilding the site now; the edition goes live in a few minutes.</p>
    <a class="linkbtn" id="commit-link" target="_blank" rel="noopener" hidden>View the commit on GitHub</a>
    <label class="flabel" for="post">Roundup post for Facebook and LinkedIn</label>
    <textarea class="field" id="post" rows="9" readonly></textarea>
    <div class="actions">
      <button type="button" class="btn primary" id="copy-post">Copy post</button>
      <a class="btn" id="card-dl" href="card.png" download>Download card.png</a>
    </div>
    <p class="msg" id="done-msg" aria-live="polite"></p>
  </div>
</section>"""

def head(cfg, title, desc, url, prefix):
    img = cfg["site_url"] + "assets/og-card.png"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{E(cfg['site_name'])}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{E(url)}"><meta property="og:image" content="{E(img)}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="robots" content="noindex">
<link rel="icon" href="{prefix}assets/icon.png">
<style>{font_css(prefix)}{PAGE_CSS}</style></head>'''

def edition_page(cfg, ed, ded):
    date = ed["edition"]
    preview = not released(ed)
    stories = ed["stories"]
    n = len(stories)
    title = f"{cfg['site_name']}: {nice(date)}"
    desc = f"{n} verified examples of AI doing good. {cfg['byline']}"
    meta = json.dumps({s["key"]: {"headline": s["headline"], "source": s["source"], "texts": s["texts"]} for s in stories}, ensure_ascii=False)
    panel, panel_js, note = "", "", ""
    if preview:
        note = '<p class="preview-note">Preview: not released yet. Only people with this link can see it.'
        if ed["intro"]["options"]:
            note += ' Choose or edit the intro, then press Commit to release it.</p>'
            panel = PANEL_HTML.replace('download>', f'download="ai-the-good-{date}.png">')
            ed_js = {"date": date, "repo": cfg["repo"], "branch": cfg.get("branch", "main"),
                     "url": f"{cfg['site_url']}{date}/", "options": ed["intro"]["options"]}
            panel_js = f"const ED = {json.dumps(ed_js, ensure_ascii=False)};{PANEL_JS}"
        else:
            note += ' The intro options and the Commit panel appear after the release-day run.</p>'
    return f'''{head(cfg, title, desc, cfg["site_url"] + date + "/", "../")}
<body><div class="wrap">
{note}
{panel}
<header>
  <a class="brand" href="../archive/">{mark(24)}{E(cfg["site_name"])}</a>
  <h1>{E(cfg["site_name"])}</h1>
  <p class="byline">{E(cfg["byline"])}</p>
  <p class="date">{nice(date)} · {n} {"story" if n == 1 else "stories"}</p>
  {dedication_html(cfg, ded)}
</header>
{intro_html(ed, preview)}
<details class="heads"><summary>All {n} headlines</summary><ul>{"".join(f'<li><a href="#{E(s["key"])}" class="jump">{E(s["teaser"])}</a></li>' for s in stories)}</ul></details>
<p class="sec">The stories</p>
<div class="list" id="list">{"".join(story_html(s, preview) for s in stories)}</div>
<footer>
  <p><a href="../archive/">Past editions</a></p>
</footer>
</div>
<script>const META = {meta}; const OPENERS = {json.dumps(cfg["openers"], ensure_ascii=False)};{PAGE_JS}{panel_js}</script>
</body></html>'''

def editions_released():
    """Released editions only: built, and Avi has committed their intro."""
    out = []
    for p in (ROOT / "data/weeks").glob("*.json"):
        if (ROOT / p.stem / "index.html").exists() and released(json.loads(p.read_text(encoding="utf-8"))):
            out.append(p.stem)
    return sorted(out, reverse=True)

def redirect_page(cfg, latest):
    if not latest:
        return f'''{head(cfg, cfg["site_name"], cfg["byline"], cfg["site_url"], "")}
<body><div class="wrap"><header><span class="brand">{mark(24)}{E(cfg["site_name"])}</span>
<h1>{E(cfg["site_name"])}</h1><p class="byline">{E(cfg["byline"])}</p></header>
<p>The first edition is on its way.</p></div></body></html>'''
    return f'''{head(cfg, cfg["site_name"], cfg["byline"], cfg["site_url"], "")}
<meta http-equiv="refresh" content="0; url=./{latest}/">
<body><p style="padding:24px"><a href="./{latest}/">Open the latest edition</a></p>
<script>location.replace('./{latest}/');</script></body></html>'''

def archive_page(cfg):
    items = []
    for w in editions_released():
        ed = json.loads((ROOT / "data/weeks" / f"{w}.json").read_text(encoding="utf-8"))
        st = ed["stories"]
        lis = "".join(f"<li>{E(s['teaser'])}</li>" for s in st[:6])
        extra = f"<li>and {len(st) - 6} more</li>" if len(st) > 6 else ""
        h = ed["intro"]["final"]["headline"]
        items.append(f'<li class="story" style="padding:16px 18px"><a href="../{w}/" style="color:inherit"><h2>{nice(w)}</h2></a>'
                     f'<p class="why">{E(h.upper())}</p><ul>{lis}{extra}</ul></li>')
    body = "".join(items) or "<li>No editions released yet.</li>"
    return f'''{head(cfg, cfg["site_name"] + ": past editions", cfg["byline"], cfg["site_url"] + "archive/", "../")}
<body><div class="wrap"><header><a class="brand" href="../">{mark(24)}{E(cfg["site_name"])}</a><h1>Past editions</h1></header>
<ul style="list-style:none;margin:0;padding:0;display:grid;gap:14px">{body}</ul></div></body></html>'''

LOG_COLS = ["date", "edition", "key", "institution", "theme", "source"]

def log_stories(ed):
    p = ROOT / "data/stories-log.csv"
    if not p.exists():
        p.write_text(",".join(LOG_COLS) + "\n", encoding="utf-8")
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    have_src = {r.get("source") for r in rows if r.get("source")}
    have_key = {(r.get("edition"), r.get("key")) for r in rows}
    with open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        for s in ed["stories"]:
            if s["source"] not in have_src and (ed["edition"], s["key"]) not in have_key:
                w.writerow([s["added"], ed["edition"], s["key"], s.get("institution", ""), s.get("theme", ""), s["source"]])

def main(edition_file):
    cfg, ed, ded = load(edition_file)
    date = ed["edition"]
    out = ROOT / date
    jobs = [(story_image_html(cfg, s), out / "img" / f"{s['key']}.png", 1080, 1080)
            for s in ed["stories"] if not (out / "img" / f"{s['key']}.png").exists()]
    if any(s.get("card") for s in ed["stories"]):
        src = card_html(cfg, ed)
        h = hashlib.sha256(src.encode()).hexdigest()[:16]
        hp = out / ".card-hash"
        if not (out / "card.png").exists() or not hp.exists() or hp.read_text().strip() != h:
            jobs.append((src, out / "card.png", 1080, 1350))
            out.mkdir(exist_ok=True); hp.write_text(h + "\n")
    if not (ROOT / "assets/og-card.png").exists():
        jobs.append((og_html(cfg), ROOT / "assets/og-card.png", 1200, 630))
    if not (ROOT / "assets/icon.png").exists():
        jobs.append((f'<body style="margin:0">{mark(64)}</body>', ROOT / "assets/icon.png", 64, 64))
    asyncio.run(render(jobs))
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(edition_page(cfg, ed, ded), encoding="utf-8")
    rel = editions_released()
    (ROOT / "index.html").write_text(redirect_page(cfg, rel[0] if rel else None), encoding="utf-8")
    (ROOT / "archive").mkdir(exist_ok=True)
    (ROOT / "archive/index.html").write_text(archive_page(cfg), encoding="utf-8")
    if ed.get("test"):
        print("Test edition: not added to data/stories-log.csv.")
    else:
        log_stories(ed)
    page = f"{cfg['site_url']}{date}/"
    n_card = sum(1 for s in ed["stories"] if s.get("card"))
    if released(ed):
        (ROOT / "data/social").mkdir(parents=True, exist_ok=True)
        post = social_post(cfg, ed)
        (ROOT / "data/social" / f"{date}.txt").write_text(post, encoding="utf-8")
        print(f"Built edition {date}: {len(ed['stories'])} stories, RELEASED (intro committed). Page: {page}\n")
        print(post)
    else:
        why = "intro options ready, waiting for Avi to commit" if ed["intro"]["options"] else "no intro options yet"
        print(f"Built edition {date}: {len(ed['stories'])} stories, {n_card} on the card, PREVIEW ({why}). Page: {page}")

if __name__ == "__main__":
    main(sys.argv[1])
