from collections.abc import Iterator
from datetime import datetime

import requests

from readwise_tools.models import Document

API_BASE_URL = "https://readwise.io/api/v3/list/"


class ReadwiseAuthError(RuntimeError):
    """Raised when READWISE_TOKEN is missing or the API rejects the token."""


class ReadwiseAPIError(RuntimeError):
    """Raised for other non-2xx API responses that aren't recoverable."""


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

        response = requests.get(
            API_BASE_URL, headers=headers, params=params, timeout=30
        )

        if response.status_code == 401:
            raise ReadwiseAuthError(
                "Readwise rejected the access token. Check READWISE_TOKEN."
            )
        if response.status_code == 429:
            raise ReadwiseAPIError(
                "Readwise API rate limit hit (HTTP 429). Try again in a minute."
            )
        response.raise_for_status()

        payload = response.json()
        for raw_doc in payload.get("results", []):
            yield Document.from_api(raw_doc)

        page_cursor = payload.get("nextPageCursor")
        if not page_cursor:
            break
