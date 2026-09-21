from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    title: str
    author: str | None
    location: str
    saved_at: datetime
    url: str | None
    source_url: str | None
    category: str | None

    @classmethod
    def from_api(cls, data: dict) -> Document:
        return cls(
            id=data["id"],
            title=data.get("title") or "(untitled)",
            author=data.get("author"),
            location=data["location"],
            saved_at=_parse_iso8601(data["saved_at"]),
            url=data.get("url"),
            source_url=data.get("source_url"),
            category=data.get("category"),
        )


def _parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value)
