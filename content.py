"""Rendu Markdown + shortcodes multimédias (sécurisé)."""
import html as _html
import re
import unicodedata
from urllib.parse import urlparse, parse_qs

import bleach
import markdown
from markupsafe import Markup, escape

VIDEO_EXT = (".mp4", ".webm", ".mov")
SHORT = re.compile(r"^[ \t]*\[\[(media|gallery|youtube):\s*(.*?)\]\][ \t]*$", re.M)
REDACT = re.compile(r"\|\|([^|\n]+?)\|\|")
OPT = re.compile(r"^(\w+)=(.*)$")

TAGS = ["p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "strong", "em", "b", "i", "del", "blockquote",
        "code", "pre", "ul", "ol", "li", "a", "img", "table", "thead", "tbody", "tr", "th", "td",
        "sup", "sub", "span"]


def _attr(tag, name, value):
    if tag == "a":
        return name in ("href", "title")
    if tag == "img":
        return name in ("src", "alt", "title")
    if tag == "span":
        return name == "class" and value == "redacted"
    return False


def slugify(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:80]


def safe_url(u):
    u = (u or "").strip()
    if u.startswith("/media/") and ".." not in u:
        return u
    p = urlparse(u)
    return u if p.scheme == "https" and p.netloc else None


def _e(v):
    return str(escape(v))


def _split(body):
    items, opts = [], {}
    for p in (x.strip() for x in body.split("|")):
        m = OPT.match(p)
        if m:
            opts[m.group(1).lower()] = m.group(2).strip()
        elif p in ("loop", "autoplay"):
            opts["loop"] = True
        elif p:
            items.append(p)
    return items, opts


def _inner(url, caption="", loop=False):
    if urlparse(url).path.lower().endswith(VIDEO_EXT):
        attrs = "autoplay loop muted" if loop else "controls"
        return f'<video src="{_e(url)}" {attrs} playsinline preload="metadata"></video>'
    return f'<img src="{_e(url)}" alt="{_e(caption)}" loading="lazy" decoding="async" data-zoom>'


def _media(items, opts):
    url = safe_url(items[0]) if items else None
    if not url:
        return ""
    align = opts.get("align", "full")
    if align not in ("left", "right", "center", "full"):
        align = "full"
    style = ""
    w = str(opts.get("width", ""))
    if w.isdigit() and 10 <= int(w) <= 100:
        style = f' style="--w:{int(w)}%"'
    cap = str(opts.get("caption", ""))
    figcap = f"<figcaption>{_e(cap)}</figcaption>" if cap else ""
    return f'<figure class="media media-{align}"{style}>{_inner(url, cap, bool(opts.get("loop")))}{figcap}</figure>'


def _gallery(items, opts):
    figs = []
    for it in items:
        u = safe_url(it)
        if u:
            figs.append(f'<figure class="media">{_inner(u, "", bool(opts.get("loop")))}</figure>')
    return f'<div class="gallery">{"".join(figs)}</div>' if figs else ""


def _youtube(items):
    raw = items[0] if items else ""
    vid = None
    if re.fullmatch(r"[\w-]{11}", raw):
        vid = raw
    else:
        p = urlparse(raw)
        if p.netloc.endswith("youtu.be"):
            vid = p.path.strip("/")[:11]
        elif "youtube" in p.netloc:
            vid = (parse_qs(p.query).get("v") or [p.path.rstrip("/").split("/")[-1]])[0][:11]
    if not vid or not re.fullmatch(r"[\w-]{11}", vid):
        return ""
    return ('<div class="embed"><iframe src="https://www.youtube-nocookie.com/embed/%s" loading="lazy" '
            'allowfullscreen referrerpolicy="strict-origin-when-cross-origin" title="Vidéo YouTube"></iframe></div>' % vid)


def _shortcode(kind, body):
    items, opts = _split(body)
    if kind == "media":
        return _media(items, opts)
    if kind == "gallery":
        return _gallery(items, opts)
    return _youtube(items)


def render(md_text):
    blocks = []

    def stash(m):
        blocks.append(_shortcode(m.group(1), m.group(2)))
        return f"\n\nZZMEDIA{len(blocks) - 1}ZZ\n\n"

    text = SHORT.sub(stash, md_text or "")
    text = REDACT.sub(r'<span class="redacted">\1</span>', text)
    out = markdown.markdown(text, extensions=["extra", "sane_lists", "nl2br"])
    out = bleach.clean(out, tags=TAGS, attributes=_attr, protocols=["http", "https", "mailto"], strip=True)
    out = out.replace("<img ", '<img loading="lazy" decoding="async" data-zoom ')
    out = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener noreferrer ugc"', out)
    for i, b in enumerate(blocks):
        tok = f"ZZMEDIA{i}ZZ"
        out = out.replace(f"<p>{tok}</p>", b).replace(tok, b)
    return Markup(out)


def plain_text(md_text):
    text = SHORT.sub("", md_text or "")
    text = REDACT.sub(r"\1", text)
    out = markdown.markdown(text, extensions=["extra", "sane_lists"])
    out = bleach.clean(out, tags=[], strip=True)
    return re.sub(r"\s+", " ", _html.unescape(out)).strip()


def normalize_tags(raw):
    tags = []
    for t in (raw or "").split(","):
        s = slugify(t)[:30]
        if s and s not in tags:
            tags.append(s)
    tags = tags[:8]
    return "," + ",".join(tags) + "," if tags else ""
