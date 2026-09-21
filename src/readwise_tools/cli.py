import argparse
import os
import sys
from datetime import UTC, datetime, timedelta

from readwise_tools.client import (
    ReadwiseAPIError,
    ReadwiseAuthError,
    ReadwiseNotFoundError,
    fetch_document_by_id,
    fetch_documents,
)
from readwise_tools.rendering import render_document

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
    get_parser.set_defaults(func=run_get)

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
        print(doc.title)
    return 0


def run_get(args: argparse.Namespace, token: str) -> int:
    try:
        document = fetch_document_by_id(token=token, doc_id=args.document_id)
    except (ReadwiseAuthError, ReadwiseAPIError, ReadwiseNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(render_document(document))
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
