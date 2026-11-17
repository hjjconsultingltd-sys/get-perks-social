"""Get Perks social graphics renderer.

Usage:
  python render.py --fonts          download brand fonts into fonts/
  python render.py --all [--force]  render every page in specs/*.json, then process uploads/*.json

A spec file is a JSON list of page specs. Every page needs "id", "template" and "format"
("post" 1080x1350 or "story" 1080x1920). Output: out/<id>.png and out/manifest.json, which maps
id -> sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False))[:16].

Templates and their fields (all text is plain text; <b>bold</b> is allowed in "body"):
  tiles      colour, kicker, headline, tiles [[icon, label] x4], note?, button, warning?
  steps      colour, kicker, headline, steps [[title, description] x3], note?, button, warning?
  tip        colour, kicker, headline, body, note?, button, warning?
  statement  colour, quote, line, button, warning?
  scorecard  colour, kicker, headline, button
  preview    image (page id of the post), date, pillar, linkedin, instagram   (format "preview": LinkedIn and
             Instagram feed mock-up of an already rendered post, for sign-off; full-height PNG, 1500px wide)
colour: "green" (employers) or "coral" (employees). icon: house, shield, will, wealth, briefcase, heart, check.
warning: true adds the mortgage repossession warning. It is required on any page that mentions mortgages.

LinkedIn uploads: a file uploads/<name>.json {"png": "<page id>", "upload_url": "...", "image_urn": "..."}
makes this script PUT out/<png>.png to upload_url and write out/uploads/<name>.json {"ok": true|false, ...}.
"""
import argparse, glob, hashlib, html, json, os, subprocess, sys, tarfile, io, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(ROOT, "fonts")
OUT = os.path.join(ROOT, "out")
WARN = "Your home may be repossessed if you do not keep up repayments on your mortgage."
FONT_PKGS = {
    "baloo-2-latin-700-normal.woff2": "@fontsource/baloo-2",
    "baloo-2-latin-800-normal.woff2": "@fontsource/baloo-2",
    "patrick-hand-latin-400-normal.woff2": "@fontsource/patrick-hand",
    "dm-sans-latin-400-normal.woff2": "@fontsource/dm-sans",
    "dm-sans-latin-500-normal.woff2": "@fontsource/dm-sans",
    "dm-sans-latin-700-normal.woff2": "@fontsource/dm-sans",
}


def get_fonts():
    os.makedirs(FONTS, exist_ok=True)
    for pkg in sorted(set(FONT_PKGS.values())):
        meta = json.load(urllib.request.urlopen(f"https://registry.npmjs.org/{pkg}/latest"))
        data = urllib.request.urlopen(meta["dist"]["tarball"]).read()
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            for m in tar.getmembers():
                name = os.path.basename(m.name)
                if name in FONT_PKGS and FONT_PKGS[name] == pkg:
                    open(os.path.join(FONTS, name), "wb").write(tar.extractfile(m).read())
    missing = [f for f in FONT_PKGS if not os.path.exists(os.path.join(FONTS, f))]
    if missing:
        sys.exit(f"missing fonts: {missing}")
    print("fonts ok")


def css():
    f = "file://" + FONTS
    return f"""
@font-face {{ font-family:'Baloo 2'; font-weight:700; src:url('{f}/baloo-2-latin-700-normal.woff2'); }}
@font-face {{ font-family:'Baloo 2'; font-weight:800; src:url('{f}/baloo-2-latin-800-normal.woff2'); }}
@font-face {{ font-family:'Patrick Hand'; font-weight:400; src:url('{f}/patrick-hand-latin-400-normal.woff2'); }}
@font-face {{ font-family:'DM Sans'; font-weight:400; src:url('{f}/dm-sans-latin-400-normal.woff2'); }}
@font-face {{ font-family:'DM Sans'; font-weight:500; src:url('{f}/dm-sans-latin-500-normal.woff2'); }}
@font-face {{ font-family:'DM Sans'; font-weight:700; src:url('{f}/dm-sans-latin-700-normal.woff2'); }}
:root {{ --green:#1FA37A; --coral:#FF6B4A; --butter:#FFFBEA; --peach:#FFF3E6; --sun:#FFD23F; --ink:#1A1A1A; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:100%; height:100%; overflow:hidden; }}
body {{ font-family:'DM Sans',sans-serif; color:#fff; -webkit-font-smoothing:antialiased; }}
.canvas {{ position:relative; width:100%; height:100%; overflow:hidden; }}
.green {{ background:var(--green); }} .coral {{ background:var(--coral); }}
.sticker {{ --s:72px; display:inline-block; font-family:'Baloo 2'; font-weight:800; font-size:var(--s); line-height:1;
  letter-spacing:-0.01em; color:var(--ink); background:var(--butter); border:calc(var(--s)*0.085) solid var(--ink);
  border-radius:999px; box-shadow:calc(var(--s)*0.12) calc(var(--s)*0.12) 0 var(--ink);
  padding:calc(var(--s)*0.2) calc(var(--s)*0.5) calc(var(--s)*0.1); transform:rotate(-3deg); white-space:nowrap; }}
.coral .sticker {{ background:var(--peach); }}
.hand {{ font-family:'Patrick Hand'; }}
.kicker {{ color:var(--butter); }} .coral .kicker {{ color:var(--peach); }}
.head {{ font-family:'Baloo 2'; font-weight:800; line-height:0.98; letter-spacing:-0.015em; }}
.tile {{ background:var(--butter); color:var(--ink); border:5px solid var(--ink); border-radius:26px; box-shadow:8px 8px 0 var(--ink);
  display:flex; align-items:center; gap:22px; padding:22px 26px; font-family:'Baloo 2'; font-weight:800; font-size:40px; line-height:1.05; }}
.coral .tile, .coral .card {{ background:var(--peach); }}
.tile svg {{ width:72px; height:72px; flex:none; }}
.card {{ background:var(--butter); color:var(--ink); border:5px solid var(--ink); border-radius:30px; box-shadow:10px 10px 0 var(--ink); }}
.btn {{ display:inline-block; background:var(--sun); color:var(--ink); border:5px solid var(--ink); border-radius:999px;
  box-shadow:7px 7px 0 var(--ink); font-family:'Baloo 2'; font-weight:800; padding:14px 40px 8px; line-height:1.1; font-size:40px; }}
.warn {{ font-size:22px; line-height:1.35; opacity:.9; }}
.float {{ position:absolute; }}
"""


ICONS = {
    "house": '<path d="M7 22 L24 8 L41 22"/><path d="M11 19 V41 H37 V19"/><path d="M20 41 V30 H28 V41"/>',
    "shield": '<path d="M24 5 L39 11 V23 C39 32 32 39 24 43 C16 39 9 32 9 23 V11 Z"/><path d="M17 24 L22 29 L31 19"/>',
    "will": '<path d="M12 5 H30 L37 12 V43 H12 Z"/><path d="M30 5 V12 H37"/><path d="M17 21 H32 M17 27 H32 M17 33 H26"/>',
    "wealth": '<path d="M24 41 V22"/><path d="M24 26 C24 18 30 13 38 13 C38 21 32 26 24 26 Z"/><path d="M24 31 C24 24 18 19 10 19 C10 27 16 31 24 31 Z"/><path d="M14 41 H34"/>',
    "briefcase": '<rect x="7" y="15" width="34" height="25" rx="5"/><path d="M18 15 V10 H30 V15"/><path d="M7 25 H41"/><path d="M24 23 V28"/>',
    "heart": '<path d="M24 41 C10 32 6 25 6 18 C6 12 10 8 15.5 8 C19.5 8 22.5 10.5 24 14 C25.5 10.5 28.5 8 32.5 8 C38 8 42 12 42 18 C42 25 38 32 24 41 Z"/>',
    "check": '<rect x="10" y="7" width="28" height="36" rx="5"/><path d="M19 7 V4 H29 V7"/><path d="M15 19 L18.5 22.5 L23 16"/><path d="M27 19 H33"/><path d="M15 31 L18.5 34.5 L23 28"/><path d="M27 31 H33"/>',
}


def icon(name):
    return (f'<svg viewBox="0 0 48 48" fill="none" stroke="#1A1A1A" stroke-width="3.6" stroke-linecap="round" '
            f'stroke-linejoin="round">{ICONS[name]}</svg>')


def spark(size, rot):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 48 48" style="transform:rotate({rot}deg)">'
            '<path d="M24 3 C25.5 15 32 22.5 45 24 C32 25.5 25.5 32 24 45 C22.5 32 16 25.5 3 24 C16 22.5 22.5 15 24 3 Z" '
            'fill="#FFD23F" stroke="#1A1A1A" stroke-width="2.6" stroke-linejoin="round"/></svg>')


def t(s):
    return html.escape(s, quote=False)


def rich(s):
    return t(s).replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")


def footer(s, story):
    note = f'<div style="font-size:{34 if story else 32}px;font-weight:500;line-height:1.3;margin-bottom:24px">{t(s["note"])}</div>' if s.get("note") else ""
    warn = s.get("warning")
    if story:
        w = f'<div class="warn" style="margin-top:24px;font-size:24px">{WARN}</div>' if warn else ""
        return f'<div style="margin-top:auto">{note}<div class="btn" style="font-size:46px">{t(s["button"])}</div>{w}</div>'
    w = f'<div class="warn" style="max-width:470px;text-align:right">{WARN}</div>' if warn else ""
    return (f'<div style="margin-top:auto">{note}<div style="display:flex;align-items:center;justify-content:space-between;gap:30px">'
            f'<div class="btn">{t(s["button"])}</div>{w}</div></div>')


def frame(s, inner, story):
    pad = "250px 90px 250px" if story else "90px 84px 64px"
    sp = f'<div class="float" style="right:{110 if story else 90}px;top:{290 if story else 92}px">{spark(68, 12 if s["colour"] == "green" else -10)}</div>'
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css()}</style></head><body>'
            f'<div class="canvas {s["colour"]}">{sp}<div style="position:absolute;inset:0;padding:{pad};display:flex;flex-direction:column">'
            f'{inner}</div></div></body></html>')


def top(s, story, size_post, size_story):
    sticker = f'<div><div class="sticker" style="--s:{88 if story else 72}px">get perks</div></div>'
    return (sticker + f'<div class="hand kicker" style="font-size:{56 if story else 46}px;margin-top:{48}px">{t(s["kicker"])}</div>'
            f'<div class="head" style="font-size:{s.get("headline_size", size_story if story else size_post)}px;margin-top:6px">{t(s["headline"])}</div>')


def tpl_tiles(s, story):
    if story:
        cells = "".join(f'<div class="tile" style="margin-top:{0 if i == 0 else 22}px;font-size:40px;padding:20px 26px">'
                        f'<div style="width:70px;height:70px;flex:none">{icon(ic)}</div><span>{t(lb)}</span></div>' for i, (ic, lb) in enumerate(s["tiles"]))
        grid = f'<div style="margin-top:44px">{cells}</div>'
    else:
        cells = "".join(f'<div class="tile">{icon(ic)}<span>{t(lb)}</span></div>' for ic, lb in s["tiles"])
        grid = f'<div style="margin-top:56px;display:grid;grid-template-columns:1fr 1fr;gap:30px">{cells}</div>'
    return top(s, story, 104, 100) + grid + footer(s, story)


def tpl_steps(s, story):
    rows = "".join(
        f'<div class="tile" style="margin-top:{0 if i == 0 else 26}px;align-items:flex-start;padding:26px 30px">'
        f'<div style="flex:none;width:76px;height:76px;border-radius:50%;background:var(--sun);border:5px solid var(--ink);display:flex;align-items:center;justify-content:center;font-size:44px;padding-top:6px">{i + 1}</div>'
        f'<div><div style="font-size:42px">{t(a)}</div><div style="font-family:\'DM Sans\';font-weight:500;font-size:28px;line-height:1.3;margin-top:6px">{t(b)}</div></div></div>'
        for i, (a, b) in enumerate(s["steps"]))
    return top(s, story, 108, 100) + f'<div style="margin-top:50px">{rows}</div>' + footer(s, story)


def tpl_tip(s, story):
    card = (f'<div class="card" style="margin-top:50px;padding:40px 44px;font-size:{44 if story else 40}px;font-weight:500;line-height:1.35">'
            f'{rich(s["body"])}</div>')
    return top(s, story, 112, 110) + card + footer(s, story)


def tpl_statement(s, story):
    sticker = f'<div><div class="sticker" style="--s:{88 if story else 72}px">get perks</div></div>'
    body = (f'<div style="margin-top:110px">'
            f'<div class="head" style="font-size:300px;line-height:.6;color:var(--sun);height:150px">&ldquo;</div>'
            f'<div class="head" style="font-size:{s.get("headline_size", 118)}px">{t(s["quote"])}</div>'
            f'<div class="hand kicker" style="font-size:62px;margin-top:34px">{t(s["line"])}</div></div>')
    return sticker + body + footer(s, story)


def tpl_scorecard(s, story):
    bars = "".join(
        f'<div style="display:flex;align-items:center;gap:20px;margin-top:22px"><div style="width:250px;font-family:\'Baloo 2\';font-weight:800;font-size:34px">{lab}</div>'
        f'<div style="flex:1;height:30px;border:4px solid var(--ink);border-radius:999px;background:#fff;overflow:hidden"><div style="width:{w}%;height:100%;background:{c};border-right:4px solid var(--ink)"></div></div></div>'
        for lab, w, c in [("Mortgages", 72, "var(--green)"), ("Protection", 45, "var(--sun)"), ("Wills", 28, "var(--coral)")])
    card = (f'<div class="card" style="margin-top:60px;padding:36px 40px 42px">'
            f'<div style="display:flex;align-items:center;gap:20px"><div style="width:70px;height:70px">{icon("check")}</div>'
            f'<div style="font-family:\'Baloo 2\';font-weight:800;font-size:44px;line-height:1">10 quick questions</div></div>{bars}</div>')
    return top(s, story, 112, 124) + card + footer(s, story)


PREVIEW_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{overflow:visible!important;height:auto!important;width:auto!important}
body{background:#F3F2EF;font-family:'DM Sans',-apple-system,sans-serif;padding:36px;width:1500px;color:#191919}
.top{font-size:22px;color:#333;margin-bottom:22px} .top b{font-size:26px}
.row{display:flex;gap:48px;align-items:flex-start}
.lbl{font-size:15px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#666;margin-bottom:10px}
.av{width:52px;height:52px;border-radius:4px;background:#1FA37A;display:flex;align-items:center;justify-content:center}
.av span{font-family:'Baloo 2';font-weight:800;font-size:11px;background:#FFFBEA;color:#1A1A1A;border:2px solid #1A1A1A;border-radius:99px;padding:2px 5px 0;transform:rotate(-3deg);white-space:nowrap}
.li{width:620px;background:#fff;border-radius:10px;border:1px solid #ddd;overflow:hidden}
.li .hd{display:flex;gap:12px;padding:14px 16px 8px} .li .nm{font-weight:700;font-size:16px} .li .sub{font-size:13px;color:#666}
.li .tx{padding:4px 16px 12px;font-size:15px;line-height:1.45} .im{width:100%;display:block}
.li .bar{display:flex;justify-content:space-around;padding:10px;border-top:1px solid #eee;color:#555;font-weight:700;font-size:14px}
.ig{width:420px;background:#fff;border-radius:34px;border:10px solid #111;overflow:hidden}
.ig .hd{display:flex;align-items:center;gap:10px;padding:12px} .ig .av{width:36px;height:36px;border-radius:50%} .ig .av span{font-size:7px;padding:1px 3px 0}
.ig .un{font-weight:700;font-size:14px} .ig .ic{padding:10px 12px 4px;font-size:22px;letter-spacing:10px}
.ig .tx{padding:4px 12px 18px;font-size:14px;line-height:1.4}
"""


def caption(text, colour):
    import re
    out = t(text).replace("\n", "<br>")
    return re.sub(r"(#\w+)", rf'<span style="color:{colour};font-weight:600">\1</span>', out)


def tpl_preview(s):
    img = "file://" + os.path.join(OUT, s["image"] + ".png")
    av = '<div class="av"><span>get perks</span></div>'
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{css()}{PREVIEW_CSS}</style></head><body>'
            f'<div class="top"><b>{t(s["image"])}</b> &middot; {t(s["date"])} &middot; {t(s["pillar"])} &middot; LinkedIn and Facebook 08:00, Instagram 12:00</div>'
            f'<div class="row"><div><div class="lbl">LinkedIn (Facebook uses the same caption)</div><div class="li">'
            f'<div class="hd">{av}<div><div class="nm">Get Perks</div><div class="sub">Company page &middot; Now &middot; Public</div></div></div>'
            f'<div class="tx">{caption(s["linkedin"], "#0A66C2")}</div><img class="im" src="{img}">'
            f'<div class="bar"><span>Like</span><span>Comment</span><span>Repost</span><span>Send</span></div></div></div>'
            f'<div><div class="lbl">Instagram</div><div class="ig"><div class="hd">{av}<div class="un">getperksuk</div></div>'
            f'<img class="im" src="{img}"><div class="ic">&#9825; &#9993; &#10148;</div>'
            f'<div class="tx"><b>getperksuk</b> {caption(s["instagram"], "#00376B")}</div></div></div></div></body></html>')


TEMPLATES = {"tiles": tpl_tiles, "steps": tpl_steps, "tip": tpl_tip, "statement": tpl_statement, "scorecard": tpl_scorecard}
SIZES = {"post": (1080, 1350), "story": (1080, 1920), "preview": (1500, 900)}


def spec_hash(spec):
    return hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def render_all(force):
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT, exist_ok=True)
    man_path = os.path.join(OUT, "manifest.json")
    manifest = json.load(open(man_path)) if os.path.exists(man_path) else {}
    pages = []
    for f in sorted(glob.glob(os.path.join(ROOT, "specs", "*.json"))):
        for spec in json.load(open(f)):
            pages.append(spec)
    pages.sort(key=lambda s: s.get("format") == "preview")
    changed = set()

    def due(s):
        if s.get("format") == "preview" and s.get("image") in changed:
            return True
        return force or manifest.get(s["id"]) != spec_hash(s) or not os.path.exists(os.path.join(OUT, s["id"] + ".png"))
    errors = []
    todo = pages
    if todo:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None)
            for s in todo:
                if not due(s):
                    continue
                try:
                    if s["format"] == "preview":
                        tmp = os.path.join(OUT, "_tmp.html")
                        open(tmp, "w").write(tpl_preview(s))
                        pg = b.new_page(viewport={"width": 1500, "height": 900})
                        pg.goto("file://" + tmp)
                        pg.evaluate("document.fonts.ready")
                        pg.wait_for_timeout(300)
                        pg.screenshot(path=os.path.join(OUT, s["id"] + ".png"), full_page=True)
                        pg.close()
                        manifest[s["id"]] = spec_hash(s)
                        print("rendered", s["id"])
                        continue
                    story = s["format"] == "story"
                    w, h = SIZES[s["format"]]
                    doc = frame(s, TEMPLATES[s["template"]](s, story), story)
                    pg = b.new_page(viewport={"width": w, "height": h})
                    tmp = os.path.join(OUT, "_tmp.html")
                    open(tmp, "w").write(doc)
                    pg.goto("file://" + tmp)
                    pg.evaluate("document.fonts.ready")
                    pg.wait_for_timeout(200)
                    over = pg.evaluate("""()=>{const W=innerWidth,H=innerHeight;const o=[];
                      document.querySelectorAll('.head,.hand,.btn,.tile,.card,.warn,.sticker').forEach(e=>{const r=e.getBoundingClientRect();
                      if(r.left<-1||r.top<-1||r.right>W+1||r.bottom>H+1)o.push(e.className)});return o}""")
                    if over:
                        raise ValueError(f"text runs off the page: {over}")
                    pg.screenshot(path=os.path.join(OUT, s["id"] + ".png"))
                    pg.close()
                    manifest[s["id"]] = spec_hash(s)
                    changed.add(s["id"])
                    print("rendered", s["id"])
                except Exception as e:
                    errors.append(f"{s.get('id')}: {e}")
                    print("FAILED", s.get("id"), e)
            b.close()
        if os.path.exists(os.path.join(OUT, "_tmp.html")):
            os.remove(os.path.join(OUT, "_tmp.html"))
    json.dump(manifest, open(man_path, "w"), indent=2, sort_keys=True)
    json.dump({"errors": errors}, open(os.path.join(OUT, "errors.json"), "w"), indent=2)
    process_uploads()


def process_uploads():
    os.makedirs(os.path.join(OUT, "uploads"), exist_ok=True)
    for f in sorted(glob.glob(os.path.join(ROOT, "uploads", "*.json"))):
        name = os.path.basename(f)
        done = os.path.join(OUT, "uploads", name)
        if os.path.exists(done):
            continue
        job = json.load(open(f))
        res = {"ok": False}
        try:
            data = open(os.path.join(OUT, job["png"] + ".png"), "rb").read()
            req = urllib.request.Request(job["upload_url"], data=data, method="PUT", headers={"Content-Type": "application/octet-stream"})
            with urllib.request.urlopen(req) as r:
                res = {"ok": 200 <= r.status < 300, "status": r.status, "image_urn": job.get("image_urn")}
        except Exception as e:
            res = {"ok": False, "error": str(e)}
        json.dump(res, open(done, "w"), indent=2)
        print("upload", name, res)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.fonts:
        get_fonts()
    if a.all:
        render_all(a.force)
