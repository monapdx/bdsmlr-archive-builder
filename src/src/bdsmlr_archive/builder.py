# src/bdsmlr_archive/builder.py
from __future__ import annotations

import json
import re
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from .templates import BASE_CSS, INDEX_JS


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120 Safari/537.36"
)


# ----------------------------
# Public API
# ----------------------------

def build_archive(
    *,
    input_files: List[Path],
    out_dir: Path,
    download_media: bool = False,
    embed_remote_media: bool = False,
    include_captions: bool = False,
    include_attribution: bool = True,
    media_max_per_post: int = 60,
    request_timeout: int = 30,
    retries: int = 3,
    sleep_between_downloads: float = 0.10,
    continue_on_download_errors: bool = True,
    user_agent: str = DEFAULT_USER_AGENT,
) -> None:
    """
    Build a static, offline-first archive from BDSMLR-style JSON exports.

    Parameters
    ----------
    input_files:
        List of JSON files (each should contain a list of dict posts).
    out_dir:
        Output directory for the generated site (e.g., "site").
    download_media:
        If True, downloads media into out_dir/media/ and rewrites pages to use local paths.
    embed_remote_media:
        If True, embeds remote media URLs directly in HTML (hotlinking). Often blocked.
        Ignored if download_media=True (local embed takes precedence).
    include_captions:
        If True, includes caption/comment lines in post pages.
    include_attribution:
        If True, includes attribution links (if present in export).
    media_max_per_post:
        Safety cap of media items per post to process.
    request_timeout:
        HTTP timeout in seconds for media downloads.
    retries:
        Download retry count.
    sleep_between_downloads:
        Delay between downloads (helps avoid rate limits/403/429).
    continue_on_download_errors:
        If True, failures are recorded but the build continues.
    user_agent:
        User-Agent header for downloads.

    Output
    ------
    Writes:
        out_dir/index.html
        out_dir/style.css
        out_dir/posts/<post_id>.html
        out_dir/data/posts.json
        out_dir/data/posts.js      (for offline double-click; no fetch())
        out_dir/data/tags.json
        out_dir/data/provenance.json
        out_dir/data/media_map.json (if download_media)
        out_dir/data/media_failures.json (if failures)
        out_dir/media/*            (if download_media)
    """
    input_files = [Path(p) for p in input_files]
    out_dir = Path(out_dir)

    if download_media and embed_remote_media:
        # Local mirror mode should take precedence; remote embed is redundant.
        embed_remote_media = False

    # Create folders
    (out_dir / "posts").mkdir(parents=True, exist_ok=True)
    (out_dir / "data").mkdir(parents=True, exist_ok=True)
    if download_media:
        (out_dir / "media").mkdir(parents=True, exist_ok=True)

    posts_raw, file_hashes = _load_all_posts(input_files)
    posts_raw = _dedupe(posts_raw)

    # ----------------------------
    # Media mirroring (optional)
    # ----------------------------
    media_map: Dict[str, str] = {}      # remote_url -> "media/<filename>"
    media_failures: List[str] = []

    if download_media:
        media_referer = _build_media_referer_map(posts_raw, media_max_per_post=media_max_per_post)
        unique_media_urls = list(media_referer.keys())
        if unique_media_urls:
            print(f"[bdsmlr-archive] Downloading media: {len(unique_media_urls)} items...")

        session = requests.Session()
        cfg = _DownloadCfg(
            timeout=request_timeout,
            retries=retries,
            sleep=sleep_between_downloads,
            continue_on_error=continue_on_download_errors,
            user_agent=user_agent,
        )

        for i, url in enumerate(unique_media_urls, start=1):
            ext = _guess_ext_from_url(url)
            fname = f"{_sha256_text(url)[:16]}.{ext}"
            local_rel = f"media/{fname}"
            local_abs = out_dir / local_rel

            referer = media_referer.get(url) or "https://bdsmlr.com/"
            ok = _download_url_to_file(url, local_abs, session=session, referer=referer, cfg=cfg)

            if ok:
                media_map[url] = local_rel
            else:
                media_failures.append(url)
                if not continue_on_download_errors:
                    raise RuntimeError(f"Failed downloading: {url}")

            if cfg.sleep:
                time.sleep(cfg.sleep)

            if i % 50 == 0:
                print(f"[bdsmlr-archive]  ...{i}/{len(unique_media_urls)}")

        _write_json(out_dir / "data" / "media_map.json", media_map)
        if media_failures:
            _write_json(out_dir / "data" / "media_failures.json", media_failures)

    # ----------------------------
    # Normalize posts + write pages
    # ----------------------------
    normalized: List[Dict[str, Any]] = []
    tags_set = set()

    for obj in posts_raw:
        post_url = obj.get("post-action-link href")
        if not isinstance(post_url, str) or not post_url:
            continue

        pid = _extract_post_id(post_url)
        when = obj.get("post-action-date") if isinstance(obj.get("post-action-date"), str) else ""

        tags = _collect_tags(obj)
        for t in tags:
            tags_set.add(t)

        media_urls = _collect_media_urls(obj)[:media_max_per_post]
        captions = _collect_captions(obj)

        # Determine what media paths we will embed:
        media_local: List[str] = []
        if download_media and media_map:
            media_local = [media_map[u] for u in media_urls if u in media_map]

        # Choose thumbnail:
        thumb = ""
        if download_media and media_local:
            # Prefer first "image-like" local item
            for u in media_urls:
                if _is_image_url(u) and u in media_map:
                    thumb = media_map[u]
                    break
            if not thumb:
                thumb = media_local[0]
        elif embed_remote_media and media_urls:
            # Prefer first image-like remote
            for u in media_urls:
                if _is_image_url(u):
                    thumb = u
                    break
            if not thumb:
                thumb = media_urls[0]

        attribution: Dict[str, str] = {}
        if include_attribution:
            for k in ["original href", "adata href", "adata", "ogname"]:
                v = obj.get(k)
                if isinstance(v, str) and v.strip():
                    attribution[k] = v.strip()

        normalized.append({
            "id": pid,
            "url": post_url,
            "when": when,
            "tags": tags,
            # index.html expects 'thumb'
            "thumb": thumb,
            # for post pages:
            "media_local": media_local,
            "media_urls": media_urls,
            "captions": captions if include_captions else [],
            "attribution": attribution,
        })

        # Write post page
        post_html = _render_post_page(
            post_id=pid,
            post_url=post_url,
            when=when,
            tags=tags,
            attribution=attribution,
            captions=captions if include_captions else [],
            download_media=download_media,
            embed_remote_media=embed_remote_media,
            media_local=media_local,
            media_urls=media_urls,
        )
        _write_text(out_dir / "posts" / f"{pid}.html", post_html)

    tags_sorted = sorted(tags_set, key=lambda s: s.lower())

    provenance = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_files": file_hashes,
        "post_count": len(normalized),
        "unique_tags": len(tags_sorted),
        "media": {
            "download_media": download_media,
            "embed_remote_media": embed_remote_media,
            "unique_media_urls": _count_unique_media_urls(posts_raw, media_max_per_post),
            "downloaded": len(media_map),
            "failed": len(media_failures),
        },
        "settings": {
            "include_captions": include_captions,
            "include_attribution": include_attribution,
            "media_max_per_post": media_max_per_post,
            "request_timeout": request_timeout,
            "retries": retries,
            "sleep_between_downloads": sleep_between_downloads,
        },
    }

    # ----------------------------
    # Write site assets
    # ----------------------------
    _write_text(out_dir / "style.css", BASE_CSS)
    _write_json(out_dir / "data" / "posts.json", normalized)
    _write_json(out_dir / "data" / "tags.json", tags_sorted)
    _write_json(out_dir / "data" / "provenance.json", provenance)

    # Offline-friendly JS data (no fetch; works via double-click)
    posts_js = "window.__POSTS__ = " + json.dumps(normalized, ensure_ascii=False) + ";\n"
    _write_text(out_dir / "data" / "posts.js", posts_js)

    index_html = _render_index_html(tags_sorted)
    _write_text(out_dir / "index.html", index_html)

    print(f"[bdsmlr-archive] Built: {out_dir.resolve()}")
    if media_failures:
        print(f"[bdsmlr-archive] WARN: Media failures: {len(media_failures)} (see data/media_failures.json)")


# ----------------------------
# Rendering
# ----------------------------

def _render_index_html(tags_sorted: List[str]) -> str:
    tag_options = '<option value="">(all tags)</option>' + "".join(
        f'<option value="{_html_escape(t)}">{_html_escape(t)}</option>' for t in tags_sorted
    )
    return f"""<!doctype html>
<html><head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Static Archive</title>
  <link rel="stylesheet" href="style.css"/>
</head>
<body>
<header>
  <h1>Static Archive</h1>
  <div class="small">
    Offline-first UI. Provenance logged. No backend.
    <span id="count"></span>
  </div>
  <div class="controls">
    <input id="search" placeholder="search tags / ids / urls" />
    <select id="tag">{tag_options}</select>
    <a class="small" href="data/provenance.json">provenance.json</a>
    <a class="small" href="data/posts.json">posts.json</a>
  </div>
</header>
<main>
  <div class="notice">
    Tip: For a fully offline archive, use <code>--download-media</code>. If using remote embed, some hosts may block hotlinking.
  </div>
  <div style="height:14px"></div>
  <div id="grid" class="grid"></div>
</main>

<script src="data/posts.js"></script>
<script>
{INDEX_JS}
</script>
</body></html>"""


def _render_post_page(
    *,
    post_id: str,
    post_url: str,
    when: str,
    tags: List[str],
    attribution: Dict[str, str],
    captions: List[str],
    download_media: bool,
    embed_remote_media: bool,
    media_local: List[str],
    media_urls: List[str],
) -> str:
    tag_block = " ".join(f"<span class='tag'>{_html_escape(t)}</span>" for t in tags)

    attrib_block = ""
    if attribution:
        items = []
        for k, v in attribution.items():
            if isinstance(v, str) and v.startswith("http"):
                items.append(
                    f"<li><span class='small'>{_html_escape(k)}:</span> "
                    f"<a href='{_html_escape(v)}' target='_blank' rel='noreferrer'>{_html_escape(v)}</a></li>"
                )
        if items:
            attrib_block = "<h3>Attribution</h3><ul>" + "".join(items) + "</ul>"

    cap_block = ""
    if captions:
        cap_block = "<h3>Notes</h3>" + "".join(f"<p>{_html_escape(c)}</p>" for c in captions)

    # Media block priority: local > remote embed > links/notice
    media_block = ""
    if download_media and media_local:
        items = []
        for rel in media_local:
            rel_esc = _html_escape("../" + rel)  # posts/ -> ../media/...
            items.append(f"""
              <div class="card">
                <a href="{rel_esc}" target="_blank" rel="noreferrer">
                  <img class="media-img" src="{rel_esc}" alt="" loading="lazy">
                </a>
                <div class="small" style="margin-top:8px; word-break:break-all;">{_html_escape(rel.split('/')[-1])}</div>
              </div>
            """)
        media_block = "<h3>Media (local)</h3><div class='grid'>" + "".join(items) + "</div>"

    elif embed_remote_media and media_urls:
        items = []
        for u in media_urls[:60]:
            u_esc = _html_escape(u)
            if _is_image_url(u):
                items.append(f"""
                  <div class="card">
                    <a href="{u_esc}" target="_blank" rel="noreferrer">
                      <img class="media-img" src="{u_esc}" alt="" loading="lazy">
                    </a>
                    <div class="small" style="margin-top:8px; word-break:break-all;">{_html_escape(u.split('/')[-1])}</div>
                  </div>
                """)
            else:
                items.append(f"<div class='card'><a href='{u_esc}' target='_blank' rel='noreferrer'>{u_esc}</a></div>")
        media_block = "<h3>Media (remote)</h3><div class='grid'>" + "".join(items) + "</div>"

    elif media_urls:
        links = "".join(
            f"<li><a href='{_html_escape(u)}' target='_blank' rel='noreferrer'>{_html_escape(u)}</a></li>"
            for u in media_urls[:60]
        )
        media_block = "<div class='notice'>Media detected but not embedded. Links:</div><ul>" + links + "</ul>"

    return f"""<!doctype html>
<html><head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>post/{_html_escape(post_id)}</title>
  <link rel="stylesheet" href="../style.css"/>
</head>
<body>
<header>
  <h1><a href="../index.html">Archive</a> / post/{_html_escape(post_id)}</h1>
  <div class="small">{_html_escape(when)}</div>
</header>
<main>
  <p><a href="{_html_escape(post_url)}" target="_blank" rel="noreferrer">Open original</a></p>
  <div class="tags">{tag_block}</div>
  <hr/>
  {attrib_block}
  {media_block}
  {cap_block}
</main>
</body></html>"""


# ----------------------------
# Download helpers
# ----------------------------

@dataclass(frozen=True)
class _DownloadCfg:
    timeout: int
    retries: int
    sleep: float
    continue_on_error: bool
    user_agent: str


def _headers_for(referer: str, *, user_agent: str) -> Dict[str, str]:
    origin = ""
    try:
        u = urlparse(referer)
        if u.scheme and u.netloc:
            origin = f"{u.scheme}://{u.netloc}"
    except Exception:
        origin = ""

    h = {
        "User-Agent": user_agent,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
    }
    if origin:
        h["Origin"] = origin
    return h


def _candidate_urls(url: str) -> List[str]:
    cands = [url]
    if "://ocdn" in url:
        cands.append(url.replace("://ocdn", "://cdn", 1))
    elif "://cdn" in url:
        cands.append(url.replace("://cdn", "://ocdn", 1))

    # Some urls come with "-og" variants
    if "-og." in url:
        cands.append(url.replace("-og.", ".", 1))

    # de-dupe preserve order
    seen = set()
    out = []
    for u in cands:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _download_url_to_file(
    url: str,
    out_path: Path,
    *,
    session: requests.Session,
    referer: str,
    cfg: _DownloadCfg,
) -> bool:
    if out_path.exists() and out_path.stat().st_size > 0:
        return True

    last_err: Optional[Exception] = None

    for attempt in range(1, cfg.retries + 1):
        for cand in _candidate_urls(url):
            try:
                headers = _headers_for(referer, user_agent=cfg.user_agent)
                with session.get(cand, headers=headers, timeout=cfg.timeout, stream=True) as r:
                    r.raise_for_status()
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = out_path.with_suffix(out_path.suffix + ".part")
                    with tmp.open("wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 128):
                            if chunk:
                                f.write(chunk)
                    tmp.replace(out_path)
                return True
            except Exception as e:
                last_err = e

        time.sleep(0.45 * attempt)

    print(f"[bdsmlr-archive] WARN: Failed to download: {url}\n  -> {out_path}\n  -> {last_err}")
    return False


def _build_media_referer_map(posts: List[Dict[str, Any]], *, media_max_per_post: int) -> Dict[str, str]:
    media_referer: Dict[str, str] = {}
    for obj in posts:
        post_url = obj.get("post-action-link href")
        if not isinstance(post_url, str) or not post_url:
            continue
        for u in _collect_media_urls(obj)[:media_max_per_post]:
            if u not in media_referer:
                media_referer[u] = post_url
    return media_referer


# ----------------------------
# Parsing helpers
# ----------------------------

def _load_all_posts(input_files: List[Path]) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    posts: List[Dict[str, Any]] = []
    file_hashes: List[Dict[str, str]] = []

    for p in input_files:
        p = Path(p)
        if not p.exists():
            continue
        file_hashes.append({"file": p.name, "sha256": _sha256_file(p)})

        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            posts.extend([x for x in data if isinstance(x, dict)])

    return posts, file_hashes


def _dedupe(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for obj in posts:
        url = obj.get("post-action-link href")
        if not isinstance(url, str) or not url:
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append(obj)
    return out


def _collect_tags(obj: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    for k, v in obj.items():
        if k.startswith("tag") and not k.startswith("tag href") and isinstance(v, str) and v.strip():
            tags.append(v.strip())
    seen = set()
    out = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _collect_media_urls(obj: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    for k, v in obj.items():
        if isinstance(v, str) and v.startswith("http"):
            if k.startswith("magnify href") or k.startswith("sidepostimage src"):
                urls.append(v)
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _collect_captions(obj: Dict[str, Any]) -> List[str]:
    caps: List[str] = []
    for k, v in obj.items():
        if k.startswith("singlecommentline") and isinstance(v, str) and v.strip():
            caps.append(v.strip())
    return caps


# ----------------------------
# Utility
# ----------------------------

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _extract_post_id(url: str) -> str:
    m = re.search(r"/post/(\d+)", url)
    return m.group(1) if m else _safe_filename(url)


def _safe_filename(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", s).strip("-")
    return s or "item"


def _is_image_url(u: str) -> bool:
    return bool(re.search(r"\.(png|jpg|jpeg|gif|webp|bmp|avif)(\?|$)", u, re.I))


def _guess_ext_from_url(u: str) -> str:
    path = urlparse(u).path
    m = re.search(r"\.([a-zA-Z0-9]{2,5})$", path)
    if m:
        ext = m.group(1).lower()
        if ext == "jpeg":
            ext = "jpg"
        return ext
    return "bin"


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&#39;")
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, obj: Any) -> None:
    _write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))


def _count_unique_media_urls(posts: List[Dict[str, Any]], media_max_per_post: int) -> int:
    seen = set()
    for obj in posts:
        for u in _collect_media_urls(obj)[:media_max_per_post]:
            seen.add(u)
    return len(seen)