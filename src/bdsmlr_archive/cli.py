import argparse
from pathlib import Path
from .builder import build_archive

def main():
    p = argparse.ArgumentParser(prog="bdsmlr-archive", description="Build a static offline archive from JSON exports.")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Build a static archive")
    b.add_argument("--input", nargs="+", required=True, help="Input JSON file(s), e.g. bdsmlr-*.json")
    b.add_argument("--out", default="site", help="Output directory (default: site)")
    b.add_argument("--download-media", action="store_true", help="Download media to out/media/ and use local paths")
    b.add_argument("--embed-remote", action="store_true", help="Embed remote media (hotlink). Not recommended.")
    b.add_argument("--include-captions", action="store_true", help="Include caption text in post pages")
    b.add_argument("--max-media-per-post", type=int, default=60, help="Cap media items per post (default: 60)")
    b.add_argument("--sleep", type=float, default=0.10, help="Delay between downloads (default: 0.10)")
    b.add_argument("--retries", type=int, default=3, help="Download retries (default: 3)")
    b.add_argument("--timeout", type=int, default=30, help="Request timeout seconds (default: 30)")

    args = p.parse_args()

    build_archive(
        input_files=[Path(x) for x in args.input],
        out_dir=Path(args.out),
        download_media=args.download_media,
        embed_remote_media=args.embed_remote,
        include_captions=args.include_captions,
        media_max_per_post=args.max_media_per_post,
        sleep_between_downloads=args.sleep,
        retries=args.retries,
        request_timeout=args.timeout,
    )