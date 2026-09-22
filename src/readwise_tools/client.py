import sys
import time
from collections.abc import Iterator
from datetime import datetime

import requests

from readwise_tools.models import Document

API_BASE_URL = "https://readwise.io/api/v3/list/"

_MAX_RETRIES = 5
_DEFAULT_RETRY_SECONDS = 5.0


class ReadwiseAuthError(RuntimeError):
    """Raised when READWISE_TOKEN is missing or the API rejects the token."""


class ReadwiseAPIError(RuntimeError):
    """Raised for other non-2xx API responses that aren't recoverable."""


class ReadwiseNotFoundError(RuntimeError):
    """Raised when no document matches the requested id."""


def fetch_document_by_id(token: str, doc_id: str) -> Document:
    """Fetch a single Reader document by id, including its HTML content."""
    headers = {"Authorization": f"Token {token}"}
    params = {"id": doc_id, "withHtmlContent": "true"}

    response = _get_with_retries(headers, params)

    results = response.json().get("results", [])
    if not results:
        raise ReadwiseNotFoundError(f"No document found with id {doc_id!r}.")

    return Document.from_api(results[0])


def fetch_documents(
    token: str,
    location: str,
    updated_after: datetime,
) -> Iterator[Document]:
    """Yield Documents for every page of the Reader `list` endpoint.

    `updatedAfter` is only a server-side pre-filter (updated_at >= saved_at
    always holds, so this can't exclude a document that should match); callers
    must still apply their own authoritative filter on `saved_at`.
    """
    headers = {"Authorization": f"Token {token}"}
    page_cursor: str | None = None

    while True:
        params: dict[str, str] = {
            "location": location,
            "updatedAfter": updated_after.isoformat(),
        }
        if page_cursor:
            params["pageCursor"] = page_cursor

        response = _get_with_retries(headers, params)

        payload = response.json()
        for raw_doc in payload.get("results", []):
            yield Document.from_api(raw_doc)

        page_cursor = payload.get("nextPageCursor")
        if not page_cursor:
            break


def _get_with_retries(
    headers: dict[str, str], params: dict[str, str]
) -> requests.Response:
    """GET the list endpoint, retrying on HTTP 429 per the Retry-After header."""
    attempt = 0
    while True:
        response = requests.get(
            API_BASE_URL, headers=headers, params=params, timeout=30
        )

        if response.status_code == 401:
            raise ReadwiseAuthError(
                "Readwise rejected the access token. Check READWISE_TOKEN."
            )

        if response.status_code == 429:
            if attempt >= _MAX_RETRIES:
                raise ReadwiseAPIError(
                    "Readwise API rate limit hit (HTTP 429) repeatedly; "
                    f"gave up after {_MAX_RETRIES} retries."
                )
            wait_seconds = _parse_retry_after(response.headers.get("Retry-After"))
            print(
                f"Rate limited by Readwise; waiting {wait_seconds:.0f}s before retrying...",
                file=sys.stderr,
            )
            time.sleep(wait_seconds)
            attempt += 1
            continue

        response.raise_for_status()
        return response


def _parse_retry_after(value: str | None) -> float:
    if value is None:
        return _DEFAULT_RETRY_SECONDS
    try:
        return max(float(value), 0.0)
    except ValueError:
        return _DEFAULT_RETRY_SECONDS
