from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
import requests

from readwise_tools.client import (
    ReadwiseAPIError,
    ReadwiseAuthError,
    ReadwiseNotFoundError,
    fetch_document_by_id,
    fetch_documents,
)

UPDATED_AFTER = datetime(2026, 9, 1, tzinfo=UTC)


def _mock_response(json_data: dict, status_code: int = 200) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data

    def raise_for_status():
        if status_code >= 400:
            raise requests.HTTPError(f"{status_code} error")

    response.raise_for_status.side_effect = raise_for_status
    return response


def _raw_doc(doc_id: str) -> dict:
    return {
        "id": doc_id,
        "title": f"Title {doc_id}",
        "author": None,
        "location": "new",
        "saved_at": "2026-09-05T00:00:00Z",
        "url": None,
        "source_url": None,
        "category": None,
    }


@patch("readwise_tools.client.requests.get")
def test_fetch_documents_single_page(mock_get):
    mock_get.return_value = _mock_response(
        {"results": [_raw_doc("a"), _raw_doc("b")], "nextPageCursor": None}
    )

    docs = list(fetch_documents("tok", "new", UPDATED_AFTER))

    assert [d.id for d in docs] == ["a", "b"]
    assert mock_get.call_count == 1
    _, kwargs = mock_get.call_args
    assert kwargs["headers"] == {"Authorization": "Token tok"}
    assert "pageCursor" not in kwargs["params"]


@patch("readwise_tools.client.requests.get")
def test_fetch_documents_multi_page_pagination(mock_get):
    mock_get.side_effect = [
        _mock_response({"results": [_raw_doc("a")], "nextPageCursor": "abc123"}),
        _mock_response({"results": [_raw_doc("b")], "nextPageCursor": None}),
    ]

    docs = list(fetch_documents("tok", "new", UPDATED_AFTER))

    assert [d.id for d in docs] == ["a", "b"]
    assert mock_get.call_count == 2
    first_kwargs = mock_get.call_args_list[0].kwargs
    second_kwargs = mock_get.call_args_list[1].kwargs
    assert "pageCursor" not in first_kwargs["params"]
    assert second_kwargs["params"]["pageCursor"] == "abc123"


@patch("readwise_tools.client.requests.get")
def test_fetch_documents_raises_auth_error_on_401(mock_get):
    mock_get.return_value = _mock_response({}, status_code=401)

    with pytest.raises(ReadwiseAuthError):
        list(fetch_documents("bad-tok", "new", UPDATED_AFTER))


@patch("readwise_tools.client.requests.get")
def test_fetch_documents_raises_api_error_on_429(mock_get):
    mock_get.return_value = _mock_response({}, status_code=429)

    with pytest.raises(ReadwiseAPIError, match="rate limit"):
        list(fetch_documents("tok", "new", UPDATED_AFTER))


@patch("readwise_tools.client.requests.get")
def test_fetch_documents_raises_on_other_http_error(mock_get):
    mock_get.return_value = _mock_response({}, status_code=500)

    with pytest.raises(requests.HTTPError):
        list(fetch_documents("tok", "new", UPDATED_AFTER))


@patch("readwise_tools.client.requests.get")
def test_fetch_documents_sends_correct_query_params(mock_get):
    mock_get.return_value = _mock_response({"results": [], "nextPageCursor": None})

    list(fetch_documents("tok", "archive", UPDATED_AFTER))

    _, kwargs = mock_get.call_args
    assert kwargs["params"]["location"] == "archive"
    assert kwargs["params"]["updatedAfter"] == UPDATED_AFTER.isoformat()


@patch("readwise_tools.client.requests.get")
def test_fetch_document_by_id_returns_document_on_success(mock_get):
    mock_get.return_value = _mock_response({"results": [_raw_doc("a")]})

    doc = fetch_document_by_id("tok", "a")

    assert doc.id == "a"
    assert mock_get.call_count == 1


@patch("readwise_tools.client.requests.get")
def test_fetch_document_by_id_sends_correct_query_params(mock_get):
    mock_get.return_value = _mock_response({"results": [_raw_doc("a")]})

    fetch_document_by_id("tok", "a")

    _, kwargs = mock_get.call_args
    assert kwargs["params"] == {"id": "a", "withHtmlContent": "true"}


@patch("readwise_tools.client.requests.get")
def test_fetch_document_by_id_raises_not_found_when_results_empty(mock_get):
    mock_get.return_value = _mock_response({"results": []})

    with pytest.raises(ReadwiseNotFoundError, match="a"):
        fetch_document_by_id("tok", "a")


@patch("readwise_tools.client.requests.get")
def test_fetch_document_by_id_raises_auth_error_on_401(mock_get):
    mock_get.return_value = _mock_response({}, status_code=401)

    with pytest.raises(ReadwiseAuthError):
        fetch_document_by_id("bad-tok", "a")


@patch("readwise_tools.client.requests.get")
def test_fetch_document_by_id_raises_api_error_on_429(mock_get):
    mock_get.return_value = _mock_response({}, status_code=429)

    with pytest.raises(ReadwiseAPIError, match="rate limit"):
        fetch_document_by_id("tok", "a")


@patch("readwise_tools.client.requests.get")
def test_fetch_document_by_id_raises_on_other_http_error(mock_get):
    mock_get.return_value = _mock_response({}, status_code=500)

    with pytest.raises(requests.HTTPError):
        fetch_document_by_id("tok", "a")
