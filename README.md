# readwise-tools

A minimal command-line tool for working with your [Readwise Reader](https://readwise.io/reader_api) library: list what you've saved, fetch and render a single article, or generate a print-ready PDF digest of everything saved to a location.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) for dependency management and running the tool
- A Readwise access token — get one at <https://readwise.io/access_token>
- **Pango**, a system library required by [WeasyPrint](https://weasyprint.org/) for the `gazette` command's PDF generation only. Not managed by `uv`; install it separately, e.g. on macOS:
  ```sh
  brew install weasyprint
  ```

## Installation

```sh
git clone <this repo>
cd readwise-tools
uv sync
export READWISE_TOKEN=<your access token>
```

Run any command with `uv run`:

```sh
uv run readwise-tools <command> [args...]
```

## Environment variables

| Variable         | Required | Description                                                                 |
|------------------|----------|-------------------------------------------------------------------------------|
| `READWISE_TOKEN` | Yes      | Your Readwise access token. Read by every command; the CLI exits with a clear error if it's unset. |

## Usage

### `list` — list saved documents by location

```
readwise-tools list <location> [days]
```

- `location`: one of `inbox`, `later`, `shortlist`, `archive`, `feed` (`inbox` maps to the Readwise API's `new` location).
- `days`: only show documents saved within this many days. Optional, defaults to `7`.

Output is one line per document, tab-separated `id<TAB>title`.

```sh
# Everything saved to your inbox in the last 7 days
uv run readwise-tools list inbox

# Everything archived in the last 30 days
uv run readwise-tools list archive 30
```

### `get` — fetch and render a single document

```
readwise-tools get <document_id> [--output {html,markdown}]
```

- `document_id`: a Readwise Reader document ID (get one from `list`'s output).
- `--output`: `html` (default) or `markdown`. Both include title/author/date/URL metadata plus the article body; `markdown` converts the body via `markdownify`, `html` prints it as-is from the API.

```sh
# Render as HTML (the default)
uv run readwise-tools get 01abc23def

# Render as Markdown instead
uv run readwise-tools get 01abc23def --output markdown
```

### `gazette` — generate a PDF digest

```
readwise-tools gazette <location> [days] [--output PATH]
```

Takes the same `location`/`days` arguments as `list`, but fetches full content for every matching document (as `get` would), concatenates them separated by `<hr />`, and renders a two-column, 9pt-serif PDF with 1/4" margins. Images are replaced with bracketed `alt`/caption text (or `[image removed]`) since they don't render reliably in the PDF.

- `--output`: destination PDF path. Optional; defaults to `gazette_<location>_<date>.pdf` in the current directory.

```sh
# Digest of everything saved to your inbox in the last 7 days
uv run readwise-tools gazette inbox

# Two weeks of archive, written to a specific file
uv run readwise-tools gazette archive 14 --output weekly.pdf
```

### Rate limiting

Readwise's API allows 20 requests/minute per endpoint. All commands automatically retry on HTTP 429, respecting the `Retry-After` header the API returns (with a short progress note printed to stderr while waiting), so a `gazette` run over a larger date window won't fail outright if it hits the limit — it just pauses and continues.

## Development

This project uses `uv` for everything — see `CLAUDE.md` for full conventions. The essentials:

```sh
uv sync                    # install locked dependencies
uv run pytest               # run tests (coverage report included)
uv run ruff check .          # lint
uv run ruff format .         # format
```
