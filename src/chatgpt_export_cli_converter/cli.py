"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .core import get_existing_conversation_ids, load_conversations, process_conversations, write_markdown_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chatgpt-export",
        description="Convert ChatGPT exports into Markdown files.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="conversations.json",
        help="Path to a ChatGPT export zip or conversations.json file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="ChatGPT",
        help="Output directory for converted Markdown files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_dir = Path(args.output)

    try:
        conversations = load_conversations(input_path)
        existing_ids = get_existing_conversation_ids(output_dir)
        results = process_conversations(conversations, existing_ids)
        write_markdown_files(results, output_dir)
    except Exception as exc:
        parser.exit(1, f"Error: {exc}\n")

    print(f"Processed: {results['processed']}")
    print(f"Skipped: {results['skipped']}")
    print(f"Errors: {results['errors']}")
    print(f"Output: {output_dir.resolve()}")
    return 0
