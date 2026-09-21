import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from readwise_tools.client import (
    ReadwiseAPIError,
    ReadwiseAuthError,
    ReadwiseNotFoundError,
    fetch_document_by_id,
    fetch_documents,
)
from readwise_tools.pdf import render_pdf
from readwise_tools.rendering import render_document, render_gazette

LOCATION_ALIASES: dict[str, str] = {
    "inbox": "new",
    "later": "later",
    "shortlist": "shortlist",
    "archive": "archive",
    "feed": "feed",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="readwise-tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List saved documents by location")
    list_parser.add_argument(
        "location",
        choices=sorted(LOCATION_ALIASES),
        help="Readwise Reader location to list (inbox, later, shortlist, archive, feed)",
    )
    list_parser.add_argument(
        "days",
        type=int,
        nargs="?",
        default=7,
        help="Only show documents saved within this many days (default: 7)",
    )
    list_parser.set_defaults(func=run_list)

    get_parser = subparsers.add_parser(
        "get", help="Fetch and render a single document by ID"
    )
    get_parser.add_argument("document_id", help="Readwise Reader document ID")
    get_parser.add_argument(
        "--output",
        choices=["html", "markdown"],
        default="html",
        help="Output format (default: html)",
    )
    get_parser.set_defaults(func=run_get)

    gazette_parser = subparsers.add_parser(
        "gazette", help="Generate a PDF digest of documents by location"
    )
    gazette_parser.add_argument(
        "location",
        choices=sorted(LOCATION_ALIASES),
        help="Readwise Reader location to include (inbox, later, shortlist, archive, feed)",
    )
    gazette_parser.add_argument(
        "days",
        type=int,
        nargs="?",
        default=7,
        help="Only include documents saved within this many days (default: 7)",
    )
    gazette_parser.add_argument(
        "--output",
        default=None,
        help="Output PDF file path (default: gazette_<location>_<date>.pdf)",
    )
    gazette_parser.set_defaults(func=run_gazette)

    return parser


def run_list(args: argparse.Namespace, token: str, now: datetime | None = None) -> int:
    api_location = LOCATION_ALIASES[args.location]
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=args.days)

    try:
        documents = fetch_documents(
            token=token, location=api_location, updated_after=cutoff
        )
        matching = [doc for doc in documents if doc.saved_at >= cutoff]
    except (ReadwiseAuthError, ReadwiseAPIError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    for doc in matching:
        print(f"{doc.id}\t{doc.title}")
    return 0


def run_get(args: argparse.Namespace, token: str) -> int:
    try:
        document = fetch_document_by_id(token=token, doc_id=args.document_id)
    except (ReadwiseAuthError, ReadwiseAPIError, ReadwiseNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(render_document(document, args.output))
    return 0


def run_gazette(
    args: argparse.Namespace, token: str, now: datetime | None = None
) -> int:
    api_location = LOCATION_ALIASES[args.location]
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=args.days)

    try:
        summaries = fetch_documents(
            token=token, location=api_location, updated_after=cutoff
        )
        matching = [doc for doc in summaries if doc.saved_at >= cutoff]
        documents = [
            fetch_document_by_id(token=token, doc_id=doc.id) for doc in matching
        ]
    except (ReadwiseAuthError, ReadwiseAPIError, ReadwiseNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not documents:
        print("No documents found for the given location/days window.")
        return 0

    output_path = (
        Path(args.output)
        if args.output
        else Path(f"gazette_{args.location}_{now.date().isoformat()}.pdf")
    )
    render_pdf(render_gazette(documents), output_path)
    print(f"Wrote {len(documents)} document(s) to {output_path}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    token = os.environ.get("READWISE_TOKEN")
    if not token:
        print(
            "Error: READWISE_TOKEN environment variable is not set. "
            "Get a token from https://readwise.io/access_token and export it.",
            file=sys.stderr,
        )
        return 1

    return args.func(args, token)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
