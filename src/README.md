# bdsmlr-archive

Generate a static, offline-first HTML archive from BDSMLR JSON exports
--- with optional full media mirroring.

This tool was originally created to archive my own blog content from
**bdsmlr.com** after exporting post data using a Chrome scraper
extension.

It turns exported `.json` files into:

-   A fully navigable static website
-   Search + tag filtering
-   Per-post HTML pages
-   Optional local media downloads (true offline mirror)
-   Provenance metadata
-   Double-clickable output (no server required)

------------------------------------------------------------------------

## 🛠 How This Was Used (My Workflow)

I used the Chrome extension:

**Easy Scraper -- One Click Web Scraper**\
https://chromewebstore.google.com/detail/easy-scraper-one-click-we/cljbfnedccphacfneigoegkiieckjndh

to scrape my own blog pages on `bdsmlr.com` and export the results as
`.json` files.

This tool then converts those exported JSON files into a structured,
offline HTML archive.

> ⚠️ Important: Only scrape and archive content you have permission to
> access and store.

------------------------------------------------------------------------

## 📦 What This Tool Generates

    site/
      index.html
      posts/
      media/            (if --download-media enabled)
      data/
        posts.json
        posts.js
        tags.json
        provenance.json
        media_map.json

The result: - Works offline - Requires no backend - No database - No
JavaScript framework - No build tools - Just static files

------------------------------------------------------------------------

## 🚀 Installation

Clone the repo:

    git clone https://github.com/YOURNAME/bdsmlr-archive-builder.git
    cd bdsmlr-archive-builder

Install in editable mode:

    pip install -e .

Python 3.9+ required.

------------------------------------------------------------------------

## 🧪 Basic Usage

Build a metadata-only archive:

    bdsmlr-archive build --input bdsmlr-*.json --out site

Build a full offline mirror (recommended):

    bdsmlr-archive build --input bdsmlr-*.json --out site --download-media

Then open:

    site/index.html

Double-click. No server required.

------------------------------------------------------------------------

## ⚙️ Options

  -----------------------------------------------------------------------
  Option                       Description
  ---------------------------- ------------------------------------------
  `--download-media`           Download all media locally into
                               `site/media/`

  `--embed-remote`             Embed remote media URLs (often blocked by
                               CDN hotlink protection)

  `--include-captions`         Include caption/comment lines in post
                               pages

  `--max-media-per-post`       Limit number of media items per post
                               (default 60)

  `--sleep`                    Delay between downloads (default 0.10s)

  `--retries`                  Retry failed downloads (default 3)

  `--timeout`                  HTTP timeout in seconds (default 30)
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 🔐 Why Local Mirroring Matters

Many CDN hosts block hotlinking (403 errors).

When using:

    --download-media

The tool:

-   Sends proper Referer headers
-   Handles cdn/ocdn variants
-   Retries failed downloads
-   Saves files with hashed filenames
-   Rewrites HTML to local paths

Result:\
A true offline archive that does not depend on the original platform
staying online.

------------------------------------------------------------------------

## 📁 Supported Input Format

The JSON files should contain a list of post dictionaries similar to
what Easy Scraper exports from BDSMLR pages.

The tool expects keys like:

-   `post-action-link href`
-   `post-action-date`
-   `magnify href`
-   `sidepostimage src`
-   `tag*`
-   `singlecommentline*`

It ignores unknown keys safely.

------------------------------------------------------------------------

## 🧠 Design Philosophy

This tool is:

-   Offline-first
-   Platform-independent
-   Transparent (provenance logged)
-   Static-only
-   No analytics
-   No tracking
-   No cloud dependency

It is intended for digital sovereignty and personal archival use.

------------------------------------------------------------------------

## ⚖️ Disclaimer

This tool does not scrape websites directly.

It operates on JSON files that you provide.

You are responsible for: - Ensuring you have permission to scrape
content - Respecting platform terms of service - Respecting copyright
and privacy laws

------------------------------------------------------------------------

## 📜 License

MIT License
