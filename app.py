"""SCP Foundation — version publique (Flask + PostgreSQL/SQLite + Discord OAuth)."""
import html
import math
import os
import secrets
import shutil
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from flask import (Flask, Response, abort, flash, jsonify, redirect, render_template, request,
                   send_from_directory, session, url_for)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import (Boolean, Column, DateTime, Integer, MetaData, String, Table, Text, and_, create_engine,
                        delete, desc, func, insert, or_, select, update)
from werkzeug.middleware.proxy_fix import ProxyFix

from content import normalize_tags, plain_text, render, safe_url, slugify

load_dotenv()

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT))
UPLOAD_DIR = DATA_DIR / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SITE_NAME = os.getenv("SITE_NAME", "SCP Foundation")
ON_RENDER = bool(os.getenv("RENDER"))
PER_PAGE = 12
MAX_IMAGE = int(os.getenv("MAX_IMAGE_MB", "12")) * 1024 * 1024
MAX_VIDEO = int(os.getenv("MAX_VIDEO_MB", "80")) * 1024 * 1024

SECTIONS = {
    "dossiers-scp": {"label": "Dossiers SCP", "icon": "◉", "desc": "Entités, objets et phénomènes anormaux."},
    "rapports-incident": {"label": "Rapports d'incident", "icon": "⚠", "desc": "Brèches, anomalies et comptes rendus."},
    "journaux-recherche": {"label": "Journaux de recherche", "icon": "⌁", "desc": "Notes et observations scientifiques."},
    "histoires": {"label": "Histoires", "icon": "▤", "desc": "Témoignages et récits du personnel."},
    "annonces": {"label": "Annonces", "icon": "◈", "desc": "Communications de la Fondation."},
}

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
secret = os.getenv("FLASK_SECRET_KEY")
if not secret:
    if ON_RENDER:
        raise RuntimeError("FLASK_SECRET_KEY doit être défini en production.")
    secret = secrets.token_hex(32)
app.secret_key = secret
app.config.update(
    MAX_CONTENT_LENGTH=MAX_VIDEO + 5 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=ON_RENDER,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    SEND_FILE_MAX_AGE_DEFAULT=timedelta(days=7),
    JSON_AS_ASCII=False,
)

limiter = Limiter(get_remote_address, app=app, default_limits=["600 per minute"],
                  storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"))


@limiter.request_filter
def _skip_limits():
    return request.endpoint in ("static", "healthz", "media")


# ---------- Base de données (PostgreSQL en prod, SQLite en local) ----------

db_url = os.getenv("DATABASE_URL")
if db_url:
    for prefix in ("postgres://", "postgresql://"):
        if db_url.startswith(prefix):
            db_url = "postgresql+psycopg://" + db_url[len(prefix):]
            break
else:
    db_url = f"sqlite:///{DATA_DIR / 'scp_site.db'}"
engine = create_engine(db_url, pool_pre_ping=True, pool_size=3, max_overflow=2, pool_recycle=300) \
    if not db_url.startswith("sqlite") else create_engine(db_url)

meta = MetaData()
posts = Table(
    "posts", meta,
    Column("id", Integer, primary_key=True),
    Column("slug", String(120), unique=True, nullable=False),
    Column("title", String(200), nullable=False),
    Column("section", String(40), nullable=False, index=True),
    Column("excerpt", Text, nullable=False, default=""),
    Column("content", Text, nullable=False),
    Column("cover", String(600)),
    Column("tags", String(300), nullable=False, default=""),
    Column("published", Boolean, nullable=False, default=False, index=True),
    Column("pinned", Boolean, nullable=False, default=False),
    Column("author", String(80)),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Column("published_at", DateTime),
)
media_t = Table(
    "media", meta,
    Column("id", Integer, primary_key=True),
    Column("key", String(200), unique=True, nullable=False),
    Column("url", String(600), nullable=False),
    Column("kind", String(10), nullable=False),
    Column("mime", String(60), nullable=False),
    Column("name", String(200)),
    Column("size", Integer),
    Column("uploaded_by", String(80)),
    Column("created_at", DateTime, nullable=False),
)
meta.create_all(engine)

CARD = [posts.c.id, posts.c.slug, posts.c.title, posts.c.section, posts.c.excerpt, posts.c.cover,
        posts.c.tags, posts.c.pinned, posts.c.published, posts.c.published_at, posts.c.created_at, posts.c.author]
DATE = func.coalesce(posts.c.published_at, posts.c.created_at)


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def seed():
    with engine.begin() as con:
        if con.execute(select(func.count()).select_from(posts)).scalar_one():
            return
        t = now()
        demo = [
            ("SCP-173 — Protocole de confinement", "dossiers-scp", "scp-173,euclide",
             "## Résumé\n**Objet :** Sculpture. **Classe :** Euclide.\n\nLe personnel doit maintenir une surveillance "
             "constante. Ne jamais ||cligner des yeux|| simultanément.\n\n> DOCUMENT FICTIF."),
            ("Incident 914 — Rapport d'analyse", "rapports-incident", "incident",
             "## Rapport interne\nLes résultats de l'expérience restent confidentiels jusqu'à validation du directeur."),
            ("Bienvenue dans les archives", "annonces", "annonce",
             "## Ouverture publique\nCe site est une œuvre de fiction inspirée de l'univers SCP."),
        ]
        for i, (title, sec, tags, content) in enumerate(demo):
            con.execute(insert(posts).values(
                slug=slugify(title) or f"doc-{i}", title=title, section=sec, tags=normalize_tags(tags),
                excerpt=plain_text(content)[:240], content=content, published=True, pinned=(i == 2),
                author="Archiviste", created_at=t, updated_at=t, published_at=t))


seed()

# ---------- Stockage des médias (disque local ou S3/R2) ----------

S3_BUCKET = os.getenv("S3_BUCKET")


class LocalStorage:
    def save(self, stream, key, mime):
        with open(UPLOAD_DIR / key, "wb") as out:
            shutil.copyfileobj(stream, out)
        return f"/media/{key}"

    def delete(self, key):
        try:
            (UPLOAD_DIR / key).unlink()
        except OSError:
            pass


class S3Storage:
    def __init__(self):
        import boto3  # installer boto3 si S3_BUCKET est utilisé
        self.bucket = S3_BUCKET
        self.public = os.environ["S3_PUBLIC_URL"].rstrip("/")
        self.client = boto3.client(
            "s3", endpoint_url=os.getenv("S3_ENDPOINT_URL"), region_name=os.getenv("S3_REGION", "auto"),
            aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"])

    def save(self, stream, key, mime):
        self.client.upload_fileobj(stream, self.bucket, key, ExtraArgs={
            "ContentType": mime, "CacheControl": "public, max-age=31536000, immutable"})
        return f"{self.public}/{key}"

    def delete(self, key):
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            app.logger.warning("Suppression S3 échouée: %s", key)


storage = S3Storage() if S3_BUCKET else LocalStorage()


def sniff(stream):
    head = stream.read(32)
    stream.seek(0)
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", "image/png", ".png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image", "image/jpeg", ".jpg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image", "image/gif", ".gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image", "image/webp", ".webp"
    if head[4:8] == b"ftyp":
        return "video", "video/mp4", ".mp4"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "video", "video/webm", ".webm"
    return None


@app.route("/media/<path:filename>")
def media(filename):
    resp = send_from_directory(UPLOAD_DIR, filename, conditional=True, max_age=31536000)
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp


# ---------- Auth & CSRF ----------

def allowed_ids():
    return {x.strip() for x in os.getenv("ADMIN_DISCORD_IDS", "").split(",") if x.strip()}


def current_user():
    return session.get("discord_user")


def is_admin():
    u, ids = current_user(), allowed_ids()
    return bool(u and ids and str(u.get("id")) in ids)


def login_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if not is_admin():
            if request.path.startswith("/admin/") and request.method == "POST" and request.accept_mimetypes.best == "application/json":
                return jsonify(error="Non autorisé"), 401
            flash("Accès réservé aux éditeurs autorisés.", "error")
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapped


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@app.before_request
def check_csrf():
    if request.method == "POST":
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
        if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
            abort(400, "Jeton de sécurité invalide. Recharge la page et réessaie.")


def redirect_uri():
    return os.getenv("DISCORD_REDIRECT_URI") or url_for("auth_callback", _external=True)


# ---------- Templates ----------

app.jinja_env.filters["md"] = render


@app.template_filter("fdate")
def fdate(d):
    return d.strftime("%d/%m/%Y") if d else ""


@app.template_filter("taglist")
def taglist(t):
    return [x for x in (t or "").split(",") if x]


@app.template_filter("reading_time")
def reading_time(text):
    return max(1, round(len((text or "").split()) / 200))


@app.template_filter("rfc822")
def rfc822(d):
    return d.replace(tzinfo=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000") if d else ""


@app.context_processor
def inject():
    return {"SECTIONS": SECTIONS, "SITE_NAME": SITE_NAME, "is_admin": is_admin(), "user": current_user(),
            "csrf_token": csrf_token}


@app.after_request
def headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    resp.headers.setdefault("Content-Security-Policy", (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data: https:; media-src 'self' https:; "
        "frame-src https://www.youtube-nocookie.com; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"))
    if ON_RENDER:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.path.startswith(("/admin", "/login", "/auth")):
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Robots-Tag"] = "noindex"
    return resp


# ---------- Pages publiques ----------

def esc_like(s):
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_posts(section=None, tag=None, q=None):
    page = max(1, request.args.get("page", 1, type=int))
    conds = [posts.c.published.is_(True)]
    if section:
        conds.append(posts.c.section == section)
    if tag:
        conds.append(posts.c.tags.like(f"%,{tag},%"))
    if q:
        pat = f"%{esc_like(q)}%"
        conds.append(or_(posts.c.title.ilike(pat, escape="\\"), posts.c.excerpt.ilike(pat, escape="\\"),
                         posts.c.content.ilike(pat, escape="\\")))
    where = and_(*conds)
    with engine.connect() as con:
        total = con.execute(select(func.count()).select_from(posts).where(where)).scalar_one()
        pages = max(1, math.ceil(total / PER_PAGE))
        page = min(page, pages)
        rows = con.execute(select(*CARD).where(where).order_by(desc(DATE))
                           .limit(PER_PAGE).offset((page - 1) * PER_PAGE)).mappings().all()
    return rows, page, pages, total


@app.route("/healthz")
def healthz():
    return "ok"


@app.route("/")
def home():
    with engine.connect() as con:
        rows = con.execute(select(*CARD).where(posts.c.published.is_(True))
                           .order_by(desc(posts.c.pinned), desc(DATE)).limit(7)).mappings().all()
        counts = dict(con.execute(select(posts.c.section, func.count()).where(posts.c.published.is_(True))
                                  .group_by(posts.c.section)).all())
    return render_template("home.html", featured=rows[0] if rows else None, latest=rows[1:], counts=counts,
                           total=sum(counts.values()))


@app.route("/archives")
def archives():
    q = request.args.get("q", "").strip()[:100]
    sec = request.args.get("section", "")
    sec = sec if sec in SECTIONS else None
    rows, page, pages, total = list_posts(section=sec, q=q)
    return render_template("archives.html", posts=rows, page=page, pages=pages, total=total, q=q,
                           current=sec, title="Archives de la Fondation", endpoint="archives",
                           args={"q": q, "section": sec or ""})


@app.route("/section/<slug>")
def section_page(slug):
    if slug not in SECTIONS:
        abort(404)
    rows, page, pages, total = list_posts(section=slug)
    return render_template("archives.html", posts=rows, page=page, pages=pages, total=total, q="", current=slug,
                           title=SECTIONS[slug]["label"], endpoint="section_page", args={"slug": slug})


@app.route("/tag/<tag>")
def tag_page(tag):
    rows, page, pages, total = list_posts(tag=slugify(tag))
    return render_template("archives.html", posts=rows, page=page, pages=pages, total=total, q="", current=None,
                           title=f"#{tag}", endpoint="tag_page", args={"tag": tag})


@app.route("/a/<slug>")
def article(slug):
    q = select(posts).where(posts.c.slug == slug)
    if not is_admin():
        q = q.where(posts.c.published.is_(True))
    with engine.connect() as con:
        post = con.execute(q).mappings().first()
        if not post:
            abort(404)
        related = con.execute(select(*CARD).where(and_(posts.c.published.is_(True), posts.c.section == post["section"],
                                                       posts.c.id != post["id"])).order_by(desc(DATE)).limit(3)).mappings().all()
    return render_template("article.html", post=post, related=related)


@app.route("/feed.xml")
def feed():
    with engine.connect() as con:
        rows = con.execute(select(*CARD).where(posts.c.published.is_(True)).order_by(desc(DATE)).limit(30)).mappings().all()
    base = os.getenv("SITE_URL", request.url_root).rstrip("/")
    items = "".join(
        f"<item><title>{html.escape(r['title'])}</title><link>{base}/a/{r['slug']}</link>"
        f"<guid>{base}/a/{r['slug']}</guid><pubDate>{rfc822(r['published_at'] or r['created_at'])}</pubDate>"
        f"<description>{html.escape(r['excerpt'] or '')}</description></item>" for r in rows)
    xml = (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{html.escape(SITE_NAME)}</title>'
           f"<link>{base}</link><description>Archives fictives de la Fondation</description>{items}</channel></rss>")
    return Response(xml, mimetype="application/rss+xml")


@app.route("/sitemap.xml")
def sitemap():
    base = os.getenv("SITE_URL", request.url_root).rstrip("/")
    with engine.connect() as con:
        rows = con.execute(select(posts.c.slug, posts.c.updated_at).where(posts.c.published.is_(True))).all()
    urls = [f"<url><loc>{base}/</loc></url>", f"<url><loc>{base}/archives</loc></url>"]
    urls += [f"<url><loc>{base}/section/{s}</loc></url>" for s in SECTIONS]
    urls += [f"<url><loc>{base}/a/{s}</loc><lastmod>{u.date().isoformat()}</lastmod></url>" for s, u in rows]
    return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    + "".join(urls) + "</urlset>", mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    base = os.getenv("SITE_URL", request.url_root).rstrip("/")
    return Response(f"User-agent: *\nDisallow: /admin\nDisallow: /login\nSitemap: {base}/sitemap.xml\n", mimetype="text/plain")


# ---------- Connexion Discord ----------

@app.route("/login")
@limiter.limit("20 per minute")
def login():
    client_id = os.getenv("DISCORD_CLIENT_ID", "")
    if not client_id:
        return render_template("login.html", setup_missing=True)
    if is_admin():
        return redirect(url_for("dashboard"))
    if request.args.get("go") != "1":
        return render_template("login.html", setup_missing=False)
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    params = {"client_id": client_id, "redirect_uri": redirect_uri(), "response_type": "code",
              "scope": "identify", "state": state}
    return redirect("https://discord.com/oauth2/authorize?" + urlencode(params))


@app.route("/auth/callback")
@limiter.limit("20 per minute")
def auth_callback():
    expected = session.pop("oauth_state", None)
    if not expected or request.args.get("state") != expected:
        abort(400, "État OAuth invalide.")
    if request.args.get("error"):
        flash("Connexion Discord annulée.", "error")
        return redirect(url_for("home"))
    code = request.args.get("code")
    if not code:
        return redirect(url_for("login"))
    try:
        tr = requests.post("https://discord.com/api/oauth2/token", data={
            "client_id": os.getenv("DISCORD_CLIENT_ID"), "client_secret": os.getenv("DISCORD_CLIENT_SECRET"),
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri()}, timeout=15)
        tr.raise_for_status()
        ur = requests.get("https://discord.com/api/users/@me",
                          headers={"Authorization": f"Bearer {tr.json()['access_token']}"}, timeout=15)
        ur.raise_for_status()
        user = ur.json()
    except Exception:
        app.logger.exception("Discord OAuth failed")
        flash("La connexion Discord a échoué. Réessaie dans un instant.", "error")
        return redirect(url_for("login"))
    ids = allowed_ids()
    if not ids or str(user.get("id")) not in ids:
        session.clear()
        return render_template("forbidden.html"), 403
    session.clear()
    session["discord_user"] = {"id": str(user["id"]), "avatar": user.get("avatar"),
                               "username": user.get("global_name") or user.get("username", "Éditeur")}
    session.permanent = True
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------- Administration ----------

@app.route("/admin")
@login_required
def dashboard():
    q = request.args.get("q", "").strip()[:100]
    stmt = select(*CARD).order_by(desc(posts.c.updated_at)).limit(300)
    if q:
        stmt = stmt.where(posts.c.title.ilike(f"%{esc_like(q)}%", escape="\\"))
    with engine.connect() as con:
        rows = con.execute(stmt).mappings().all()
        total = con.execute(select(func.count()).select_from(posts)).scalar_one()
        pub = con.execute(select(func.count()).select_from(posts).where(posts.c.published.is_(True))).scalar_one()
        nmedia = con.execute(select(func.count()).select_from(media_t)).scalar_one()
    return render_template("admin.html", posts=rows, q=q, stats={"total": total, "pub": pub, "draft": total - pub, "media": nmedia})


def form_data(post=None):
    f = request.form
    if f:
        return {"title": f.get("title", ""), "section": f.get("section", "annonces"), "excerpt": f.get("excerpt", ""),
                "tags": f.get("tags", ""), "cover": f.get("cover", ""), "content": f.get("content", ""),
                "published": f.get("published") == "on", "pinned": f.get("pinned") == "on"}
    if post:
        return {**{k: post[k] for k in ("title", "section", "excerpt", "cover", "content", "published", "pinned")},
                "tags": ", ".join(taglist(post["tags"]))}
    return {"title": "", "section": "dossiers-scp", "excerpt": "", "tags": "", "cover": "", "content": "",
            "published": False, "pinned": False}


@app.route("/admin/new", methods=["GET", "POST"])
@app.route("/admin/edit/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id=None):
    post = None
    if post_id is not None:
        with engine.connect() as con:
            post = con.execute(select(posts).where(posts.c.id == post_id)).mappings().first()
        if not post:
            abort(404)
    if request.method == "POST":
        data = form_data(post)
        title, content = data["title"].strip()[:200], data["content"].strip()
        if not title or not content or data["section"] not in SECTIONS:
            flash("Titre, section et contenu sont obligatoires.", "error")
            return render_template("editor.html", post=post, data=data)
        cover = data["cover"].strip()
        cover = cover if cover and safe_url(cover) else None
        vals = dict(title=title, section=data["section"], content=content, cover=cover,
                    excerpt=data["excerpt"].strip()[:300] or plain_text(content)[:240],
                    tags=normalize_tags(data["tags"]), published=data["published"], pinned=data["pinned"],
                    updated_at=now())
        with engine.begin() as con:
            if post:
                if vals["published"] and not post["published_at"]:
                    vals["published_at"] = now()
                con.execute(update(posts).where(posts.c.id == post["id"]).values(**vals))
                slug = post["slug"]
            else:
                base = slugify(title) or "document"
                slug, n = base, 2
                while con.execute(select(posts.c.id).where(posts.c.slug == slug)).first():
                    slug, n = f"{base}-{n}", n + 1
                con.execute(insert(posts).values(**vals, slug=slug, author=current_user()["username"],
                                                 created_at=now(), published_at=now() if vals["published"] else None))
        flash("Document enregistré.", "success")
        return redirect(url_for("article", slug=slug) if vals["published"] else url_for("dashboard"))
    return render_template("editor.html", post=post, data=form_data(post))


@app.post("/admin/toggle/<int:post_id>")
@login_required
def toggle_post(post_id):
    with engine.begin() as con:
        p = con.execute(select(posts.c.published, posts.c.published_at).where(posts.c.id == post_id)).first()
        if p:
            vals = {"published": not p.published, "updated_at": now()}
            if not p.published and not p.published_at:
                vals["published_at"] = now()
            con.execute(update(posts).where(posts.c.id == post_id).values(**vals))
    flash("Visibilité mise à jour.", "success")
    return redirect(url_for("dashboard"))


@app.post("/admin/delete/<int:post_id>")
@login_required
def delete_post(post_id):
    with engine.begin() as con:
        con.execute(delete(posts).where(posts.c.id == post_id))
    flash("Document supprimé.", "success")
    return redirect(url_for("dashboard"))


@app.post("/admin/preview")
@login_required
def preview():
    return jsonify(html=str(render((request.get_json(silent=True) or {}).get("content", ""))))


@app.get("/admin/media")
@login_required
def media_list():
    with engine.connect() as con:
        rows = con.execute(select(media_t).order_by(desc(media_t.c.id)).limit(120)).mappings().all()
    return jsonify(items=[{"id": r["id"], "url": r["url"], "kind": r["kind"], "name": r["name"]} for r in rows])


@app.post("/admin/upload")
@login_required
@limiter.limit("60 per minute")
def upload():
    out, errors = [], []
    for f in request.files.getlist("files"):
        info = sniff(f.stream)
        if not info:
            errors.append(f"{f.filename} : format non pris en charge (PNG, JPG, GIF, WEBP, MP4, WEBM).")
            continue
        kind, mime, ext = info
        f.stream.seek(0, 2)
        size = f.stream.tell()
        f.stream.seek(0)
        if size > (MAX_VIDEO if kind == "video" else MAX_IMAGE):
            errors.append(f"{f.filename} : fichier trop volumineux.")
            continue
        key = secrets.token_hex(14) + ext
        url = storage.save(f.stream, key, mime)
        with engine.begin() as con:
            mid = con.execute(insert(media_t).values(
                key=key, url=url, kind=kind, mime=mime, name=(f.filename or "")[:200], size=size,
                uploaded_by=current_user()["username"], created_at=now())).inserted_primary_key[0]
        out.append({"id": mid, "url": url, "kind": kind, "name": f.filename})
    return jsonify(items=out, errors=errors)


@app.post("/admin/media/<int:media_id>/delete")
@login_required
def media_delete(media_id):
    with engine.begin() as con:
        row = con.execute(select(media_t.c.key).where(media_t.c.id == media_id)).first()
        con.execute(delete(media_t).where(media_t.c.id == media_id))
    if row:
        storage.delete(row.key)
    return jsonify(ok=True)


# ---------- Erreurs ----------

@app.errorhandler(404)
def e404(_):
    return render_template("error.html", code=404, message="Ce dossier n'existe pas ou n'est pas disponible."), 404


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(413)
@app.errorhandler(429)
@app.errorhandler(500)
def error_page(e):
    code = getattr(e, "code", 500)
    msgs = {400: getattr(e, "description", "Requête invalide."), 403: "Accès refusé.",
            413: "Fichier trop volumineux.", 429: "Trop de requêtes. Patiente un instant.",
            500: "Une anomalie est survenue. Réessaie plus tard."}
    if request.path.startswith("/admin/") and request.method == "POST":
        return jsonify(error=msgs.get(code, "Erreur")), code
    return render_template("error.html", code=code, message=msgs.get(code, "Erreur")), code


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", host="127.0.0.1", port=int(os.getenv("PORT", "5000")))
