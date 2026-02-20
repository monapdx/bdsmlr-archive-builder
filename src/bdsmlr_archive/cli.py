# src/bdsmlr_archive/cli.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .builder import build_archive


def _collect_json_files_from_dir(dir_path: Path) -> list[Path]:
    if not dir_path.exists() or not dir_path.is_dir():
        return []
    # Only top-level .json files (simple + predictable for beginners)
    return sorted([p for p in dir_path.iterdir() if p.is_file() and p.suffix.lower() == ".json"])


def main(argv: list[str] | None = None) -> None:
    """
    bdsmlr-archive CLI

    Beginner-friendly defaults:
      - If --input is omitted, reads all .json files from ./exports/
      - If --out is omitted, writes to ./output/
      - If neither --download-media nor --embed-remote is specified,
        defaults to --download-media (best chance of working offline).
    """
    if argv is None:
        argv = sys.argv[1:]

    p = argparse.ArgumentParser(
        prog="bdsmlr-archive",
        description="Build a static offline archive from JSON exports.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Build a static archive")
    b.add_argument(
        "--input",
        nargs="*",
        default=None,
        help="Input JSON file(s). If omitted, uses all .json files in ./exports/",
    )
    b.add_argument(
        "--input-dir",
        default=None,
        help="Directory containing .json exports (alternative to --input). Defaults to ./exports/ if --input is omitted.",
    )
    b.add_argument(
        "--out",
        default="output",
        help="Output directory (default: output)",
    )

    mode = b.add_mutually_exclusive_group()
    mode.add_argument(
        "--download-media",
        action="store_true",
        help="Download media into out/media/ and use local paths (recommended)",
    )
    mode.add_argument(
        "--embed-remote",
        action="store_true",
        help="Embed remote media URLs (hotlinking; often blocked)",
    )
    mode.add_argument(
        "--no-media",
        action="store_true",
        help="Do not embed or download media (metadata-only pages)",
    )

    b.add_argument(
        "--include-captions",
        action="store_true",
        help="Include caption/comment lines in post pages",
    )
    b.add_argument(
        "--max-media-per-post",
        type=int,
        default=60,
        help="Cap media items per post (default: 60)",
    )
    b.add_argument(
        "--sleep",
        type=float,
        default=0.10,
        help="Delay between downloads in seconds (default: 0.10)",
    )
    b.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Download retries (default: 3)",
    )
    b.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout seconds (default: 30)",
    )

    args = p.parse_args(argv)

    if args.cmd == "build":
        cwd = Path.cwd()

        # Decide input directory
        input_dir = Path(args.input_dir) if args.input_dir else (cwd / "exports")

        # Determine input files
        input_files: list[Path] = []
        if args.input is None:
            # argparse won't hit this because default=None only if flag omitted;
            # but we used nargs="*" + default=None so this is our "omitted" sentinel.
            input_files = _collect_json_files_from_dir(input_dir)
        elif len(args.input) == 0:
            # User passed --input with nothing (rare); treat as omitted.
            input_files = _collect_json_files_from_dir(input_dir)
        else:
            input_files = [Path(x) for x in args.input]

        # If any of the provided input paths are directories, expand them
        expanded: list[Path] = []
        for pth in input_files:
            if pth.exists() and pth.is_dir():
                expanded.extend(_collect_json_files_from_dir(pth))
            else:
                expanded.append(pth)
        input_files = expanded

        # Beginner-friendly error message
        if not input_files:
            raise SystemExit(
                "No input JSON files found.\n\n"
                "Put your exported .json files in the 'exports' folder (next to where you run the command),\n"
                "or pass them explicitly:\n"
                "  bdsmlr-archive build --input yourfile.json\n"
                "or:\n"
                "  bdsmlr-archive build --input-dir path\\to\\exports\n"
            )

        # Choose media behavior
        if args.no_media:
            download_media = False
            embed_remote = False
        elif args.embed_remote:
            download_media = False
            embed_remote = True
        elif args.download_media:
            download_media = True
            embed_remote = False
        else:
            # Default behavior for non-technical users: download media locally
            download_media = True
            embed_remote = False

        build_archive(
            input_files=input_files,
            out_dir=Path(args.out),
            download_media=download_media,
            embed_remote_media=embed_remote,
            include_captions=args.include_captions,
            media_max_per_post=args.max_media_per_post,
            sleep_between_downloads=args.sleep,
            retries=args.retries,
            request_timeout=args.timeout,
        )
        return


if __name__ == "__main__":
    main()