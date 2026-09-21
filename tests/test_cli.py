from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from readwise_tools.cli import (
    LOCATION_ALIASES,
    build_parser,
    main,
    run_gazette,
    run_get,
    run_list,
)
from readwise_tools.client import (
    ReadwiseAPIError,
    ReadwiseAuthError,
    ReadwiseNotFoundError,
)
from readwise_tools.models import Document

NOW = datetime(2026, 9, 21, tzinfo=UTC)


def _doc(doc_id: str, days_ago: int) -> Document:
    return Document(
        id=doc_id,
        title=f"Title {doc_id}",
        author=None,
        location="new",
        saved_at=NOW - timedelta(days=days_ago),
        url=None,
        source_url=None,
        category=None,
    )


def test_build_parser_translates_inbox_to_new():
    parser = build_parser()
    args = parser.parse_args(["list", "inbox", "3"])

    assert args.location == "inbox"
    assert LOCATION_ALIASES["inbox"] == "new"


def test_days_defaults_to_seven():
    parser = build_parser()
    args = parser.parse_args(["list", "archive"])
    assert args.days == 7


def test_days_explicit_value_parsed_as_int():
    parser = build_parser()
    args = parser.parse_args(["list", "inbox", "30"])
    assert args.days == 30
    assert isinstance(args.days, int)


def test_invalid_location_rejected_by_argparse(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["list", "bogus"])
    capsys.readouterr()


@patch("readwise_tools.cli.fetch_documents")
def test_run_list_filters_by_saved_at_window(mock_fetch, capsys):
    mock_fetch.return_value = [_doc("in", 3), _doc("out", 8)]
    parser = build_parser()
    args = parser.parse_args(["list", "inbox", "7"])

    exit_code = run_list(args, token="tok", now=NOW)

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Title in" in out
    assert "Title out" not in out
    _, kwargs = mock_fetch.call_args
    assert kwargs["location"] == "new"


@patch("readwise_tools.cli.fetch_documents")
def test_run_list_prints_id_and_title(mock_fetch, capsys):
    mock_fetch.return_value = [_doc("a", 1), _doc("b", 2)]
    parser = build_parser()
    args = parser.parse_args(["list", "archive"])

    run_list(args, token="tok", now=NOW)

    lines = capsys.readouterr().out.splitlines()
    assert lines == ["a\tTitle a", "b\tTitle b"]


@patch("readwise_tools.cli.fetch_documents")
def test_run_list_handles_auth_error(mock_fetch, capsys):
    mock_fetch.side_effect = ReadwiseAuthError("bad token")
    parser = build_parser()
    args = parser.parse_args(["list", "inbox"])

    exit_code = run_list(args, token="tok", now=NOW)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "bad token" in captured.err


@patch("readwise_tools.cli.fetch_documents")
def test_run_list_handles_api_error(mock_fetch, capsys):
    mock_fetch.side_effect = ReadwiseAPIError("rate limited")
    parser = build_parser()
    args = parser.parse_args(["list", "inbox"])

    exit_code = run_list(args, token="tok", now=NOW)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "rate limited" in captured.err


def test_main_exits_nonzero_when_token_missing(monkeypatch, capsys):
    monkeypatch.delenv("READWISE_TOKEN", raising=False)
    monkeypatch.setattr("sys.argv", ["readwise-tools", "list", "inbox"])

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "READWISE_TOKEN" in captured.err


@patch("readwise_tools.cli.fetch_documents")
def test_main_dispatches_to_run_list_when_token_present(
    mock_fetch, monkeypatch, capsys
):
    monkeypatch.setenv("READWISE_TOKEN", "tok")
    monkeypatch.setattr("sys.argv", ["readwise-tools", "list", "inbox"])
    mock_fetch.return_value = [_doc("a", 1)]

    exit_code = main()

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Title a" in out


def test_build_parser_get_subcommand_parses_document_id():
    parser = build_parser()
    args = parser.parse_args(["get", "abc123"])

    assert args.document_id == "abc123"
    assert args.func is run_get


def test_build_parser_get_output_defaults_to_html():
    parser = build_parser()
    args = parser.parse_args(["get", "a"])

    assert args.output == "html"


def test_build_parser_get_output_accepts_markdown():
    parser = build_parser()
    args = parser.parse_args(["get", "a", "--output", "markdown"])

    assert args.output == "markdown"


def test_build_parser_get_output_rejects_invalid_choice(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["get", "a", "--output", "bogus"])
    capsys.readouterr()


@patch("readwise_tools.cli.render_document")
@patch("readwise_tools.cli.fetch_document_by_id")
def test_run_get_happy_path_prints_rendered_output(mock_fetch, mock_render, capsys):
    mock_fetch.return_value = _doc("a", 1)
    mock_render.return_value = "RENDERED OUTPUT"
    parser = build_parser()
    args = parser.parse_args(["get", "a"])

    exit_code = run_get(args, token="tok")

    out = capsys.readouterr().out
    assert exit_code == 0
    assert out == "RENDERED OUTPUT\n"
    mock_fetch.assert_called_once_with(token="tok", doc_id="a")
    mock_render.assert_called_once_with(mock_fetch.return_value, "html")


@patch("readwise_tools.cli.render_document")
@patch("readwise_tools.cli.fetch_document_by_id")
def test_run_get_passes_explicit_output_format(mock_fetch, mock_render):
    mock_fetch.return_value = _doc("a", 1)
    mock_render.return_value = "RENDERED OUTPUT"
    parser = build_parser()
    args = parser.parse_args(["get", "a", "--output", "markdown"])

    run_get(args, token="tok")

    mock_render.assert_called_once_with(mock_fetch.return_value, "markdown")


@patch("readwise_tools.cli.fetch_document_by_id")
def test_run_get_handles_not_found_error(mock_fetch, capsys):
    mock_fetch.side_effect = ReadwiseNotFoundError("not found")
    parser = build_parser()
    args = parser.parse_args(["get", "bogus"])

    exit_code = run_get(args, token="tok")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "not found" in captured.err


@patch("readwise_tools.cli.fetch_document_by_id")
def test_run_get_handles_auth_error(mock_fetch, capsys):
    mock_fetch.side_effect = ReadwiseAuthError("bad token")
    parser = build_parser()
    args = parser.parse_args(["get", "a"])

    exit_code = run_get(args, token="tok")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "bad token" in captured.err


@patch("readwise_tools.cli.fetch_document_by_id")
def test_run_get_handles_api_error(mock_fetch, capsys):
    mock_fetch.side_effect = ReadwiseAPIError("rate limited")
    parser = build_parser()
    args = parser.parse_args(["get", "a"])

    exit_code = run_get(args, token="tok")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "rate limited" in captured.err


@patch("readwise_tools.cli.render_document")
@patch("readwise_tools.cli.fetch_document_by_id")
def test_main_dispatches_to_run_get_when_token_present(
    mock_fetch, mock_render, monkeypatch, capsys
):
    monkeypatch.setenv("READWISE_TOKEN", "tok")
    monkeypatch.setattr("sys.argv", ["readwise-tools", "get", "abc123"])
    mock_fetch.return_value = _doc("a", 1)
    mock_render.return_value = "RENDERED"

    exit_code = main()

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "RENDERED" in out
    mock_render.assert_called_once_with(mock_fetch.return_value, "html")


def test_build_parser_gazette_defaults():
    parser = build_parser()
    args = parser.parse_args(["gazette", "inbox"])

    assert args.location == "inbox"
    assert args.days == 7
    assert args.output is None
    assert args.func is run_gazette


def test_build_parser_gazette_accepts_explicit_days_and_output():
    parser = build_parser()
    args = parser.parse_args(["gazette", "archive", "14", "--output", "out.pdf"])

    assert args.days == 14
    assert args.output == "out.pdf"


@patch("readwise_tools.cli.render_pdf")
@patch("readwise_tools.cli.render_gazette")
@patch("readwise_tools.cli.fetch_document_by_id")
@patch("readwise_tools.cli.fetch_documents")
def test_run_gazette_happy_path_uses_default_filename(
    mock_fetch_list, mock_fetch_one, mock_render_gazette, mock_render_pdf, capsys
):
    mock_fetch_list.return_value = [_doc("a", 1), _doc("b", 2)]
    full_docs = [_doc("a", 1), _doc("b", 2)]
    mock_fetch_one.side_effect = full_docs
    mock_render_gazette.return_value = "<html>gazette</html>"
    parser = build_parser()
    args = parser.parse_args(["gazette", "inbox"])

    exit_code = run_gazette(args, token="tok", now=NOW)

    out = capsys.readouterr().out
    assert exit_code == 0
    expected_path = Path("gazette_inbox_2026-09-21.pdf")
    assert str(expected_path) in out
    mock_fetch_one.assert_any_call(token="tok", doc_id="a")
    mock_fetch_one.assert_any_call(token="tok", doc_id="b")
    mock_render_gazette.assert_called_once_with(full_docs)
    mock_render_pdf.assert_called_once_with("<html>gazette</html>", expected_path)


@patch("readwise_tools.cli.render_pdf")
@patch("readwise_tools.cli.render_gazette")
@patch("readwise_tools.cli.fetch_document_by_id")
@patch("readwise_tools.cli.fetch_documents")
def test_run_gazette_uses_explicit_output_path(
    mock_fetch_list, mock_fetch_one, mock_render_gazette, mock_render_pdf
):
    mock_fetch_list.return_value = [_doc("a", 1)]
    mock_fetch_one.return_value = _doc("a", 1)
    mock_render_gazette.return_value = "<html>gazette</html>"
    parser = build_parser()
    args = parser.parse_args(["gazette", "inbox", "--output", "custom.pdf"])

    run_gazette(args, token="tok", now=NOW)

    mock_render_pdf.assert_called_once_with("<html>gazette</html>", Path("custom.pdf"))


@patch("readwise_tools.cli.render_gazette")
@patch("readwise_tools.cli.fetch_documents")
def test_run_gazette_handles_empty_match_list(
    mock_fetch_list, mock_render_gazette, capsys
):
    mock_fetch_list.return_value = []
    parser = build_parser()
    args = parser.parse_args(["gazette", "inbox"])

    exit_code = run_gazette(args, token="tok", now=NOW)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No documents found" in captured.out
    mock_render_gazette.assert_not_called()


@patch("readwise_tools.cli.fetch_documents")
def test_run_gazette_handles_auth_error_from_list_fetch(mock_fetch_list, capsys):
    mock_fetch_list.side_effect = ReadwiseAuthError("bad token")
    parser = build_parser()
    args = parser.parse_args(["gazette", "inbox"])

    exit_code = run_gazette(args, token="tok", now=NOW)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "bad token" in captured.err


@patch("readwise_tools.cli.fetch_document_by_id")
@patch("readwise_tools.cli.fetch_documents")
def test_run_gazette_handles_api_error_from_item_fetch(
    mock_fetch_list, mock_fetch_one, capsys
):
    mock_fetch_list.return_value = [_doc("a", 1)]
    mock_fetch_one.side_effect = ReadwiseAPIError("rate limited")
    parser = build_parser()
    args = parser.parse_args(["gazette", "inbox"])

    exit_code = run_gazette(args, token="tok", now=NOW)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "rate limited" in captured.err


@patch("readwise_tools.cli.render_pdf")
@patch("readwise_tools.cli.render_gazette")
@patch("readwise_tools.cli.fetch_document_by_id")
@patch("readwise_tools.cli.fetch_documents")
def test_main_dispatches_to_run_gazette_when_token_present(
    mock_fetch_list,
    mock_fetch_one,
    mock_render_gazette,
    mock_render_pdf,
    monkeypatch,
    capsys,
):
    monkeypatch.setenv("READWISE_TOKEN", "tok")
    monkeypatch.setattr("sys.argv", ["readwise-tools", "gazette", "inbox"])
    mock_fetch_list.return_value = [_doc("a", 1)]
    mock_fetch_one.return_value = _doc("a", 1)
    mock_render_gazette.return_value = "<html>gazette</html>"

    exit_code = main()

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Wrote 1 document(s)" in out
    mock_render_pdf.assert_called_once()
