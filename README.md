# bdsmlr-archive

Generate a static, offline-first HTML archive from **BDSMLR** JSON exports — with optional full media mirroring (so it works fully offline).

This tool was originally created to archive my own blog content from **bdsmlr.com** after exporting post data using a Chrome scraper extension.

It turns exported `.json` files into:

- A browsable static website (index + per-post pages)
- Search + tag filtering
- Optional local media downloads (true offline mirror)
- Provenance metadata
- **Double-clickable output** (no server required)

---

## 🛠 How This Was Used (My Workflow)

I used the Chrome extension:

**Easy Scraper (One Click Web Scraper)**  
https://chromewebstore.google.com/detail/easy-scraper-one-click-we/cljbfnedccphacfneigoegkiieckjndh

…to scrape my own blog pages on `bdsmlr.com` and export the results as `.json` files.

This tool converts those exported JSON files into a structured, offline HTML archive.

> ⚠️ Important: Only scrape and archive content you have permission to access and store.

---

## ✅ Quick Start (Beginner-Friendly)

**Goal:** “Drop the JSON files in a folder → run one command → open the archive.”

1) Put your exported `.json` files into the `exports/` folder (next to this project).

2) Build your archive (recommended: local media mirroring):

```bash
bdsmlr-archive build
```

3) Open the result:

- `output/index.html` (double-click)

### What `bdsmlr-archive build` does by default

If you do not pass any arguments, the tool will:

- Read all `.json` files from `./exports/`
- Write the archive to `./output/`
- **Download media** and embed it locally (best chance of working offline)

This “no-args” default is intentional to make the tool accessible for non-technical users.

---

## 📦 What This Tool Generates

```
output/
  index.html
  posts/
  media/            (if media is downloaded)
  data/
    posts.json
    posts.js
    tags.json
    provenance.json
    media_map.json
```

The result:

- Works offline
- Requires no backend
- No database
- No JavaScript framework
- No build tools
- Just static files

---

## 🚀 Installation

Clone the repo:

```bash
git clone https://github.com/monapdx/bdsmlr-archive-builder.git
cd bdsmlr-archive-builder
```

Install in editable mode:

```bash
pip install -e .
```

Python 3.9+ required.

> Tip: If you prefer not to use editable installs, you can also run the CLI via:
> `python -m bdsmlr_archive.cli --help`

---

## 🧪 Usage

### Build using the beginner defaults

```bash
bdsmlr-archive build
```

### Build with explicit input files

```bash
bdsmlr-archive build --input exports/file1.json exports/file2.json
```

### Build from a specific exports folder

```bash
bdsmlr-archive build --input-dir exports --out output
```

### Metadata-only (no embeds, no downloads)

```bash
bdsmlr-archive build --no-media
```

### Remote hotlink embed (not recommended; often blocked)

```bash
bdsmlr-archive build --embed-remote
```

---

## ⚙️ Options (build)

| Option | Description |
|--------|------------|
| `--input [FILES...]` | Input JSON file(s). If omitted, uses all `.json` in `./exports/` |
| `--input-dir DIR` | Directory containing `.json` exports |
| `--out DIR` | Output directory (default: `output`) |
| `--download-media` | Download all media locally into `out/media/` (recommended) |
| `--embed-remote` | Embed remote media URLs (hotlinking; often blocked by CDN protection) |
| `--no-media` | Do not embed or download media (metadata-only pages) |
| `--include-captions` | Include caption/comment lines in post pages |
| `--max-media-per-post N` | Limit media items per post (default: 60) |
| `--sleep SECONDS` | Delay between downloads (default: 0.10) |
| `--retries N` | Retry failed downloads (default: 3) |
| `--timeout SECONDS` | HTTP timeout seconds (default: 30) |

---

## 🔐 Why Local Mirroring Matters

Many CDN hosts block hotlinking (403 errors). When you use local mirroring, the tool:

- Sends Referer/Origin headers (to reduce 403s)
- Handles `cdn`/`ocdn` variants
- Retries failed downloads
- Saves files with hashed filenames
- Rewrites HTML to local paths

Result: a true offline archive that does not depend on the original platform staying online.

---

## 📁 Supported Input Format

The JSON files should contain a list of post dictionaries similar to what Easy Scraper exports from BDSMLR pages.

The tool looks for keys like:

- `post-action-link href`
- `post-action-date`
- `magnify href`
- `sidepostimage src`
- `tag*`
- `singlecommentline*`

Unknown keys are ignored safely.

---

## 🧠 Design Philosophy

This tool is:

- Offline-first
- Platform-independent
- Transparent (provenance logged)
- Static-only
- No analytics
- No tracking
- No cloud dependency

It’s intended for digital sovereignty and personal archival use.

---

## ⚖️ Disclaimer

This tool does **not** scrape websites directly. It operates on JSON files that you provide.

You are responsible for:

- Ensuring you have permission to scrape content
- Respecting platform terms of service
- Respecting copyright and privacy laws

---

## 📜 License

MIT License
