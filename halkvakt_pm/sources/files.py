"""File-based sources: CSV and JSON/JSONL exports from any tool.

Most trackers and social tools can export CSV or JSON, so these two sources
cover a lot of ground before a dedicated API integration exists.

Config keys:
  path       file path (relative to the config file)
  channel    bug_tracker | social | email | support | other
  fields     optional mapping from FeedbackItem field -> column/key name,
             e.g. {text = "body", author = "user.screen_name"}
  meta       optional list of extra columns/keys to pass to the model
"""

from __future__ import annotations

import csv
import json
import os
from typing import Any, Iterable

from ..models import FeedbackItem
from .base import Source, register

DEFAULT_FIELDS = {
    "id": "id",
    "title": "title",
    "text": "text",
    "author": "author",
    "created_at": "created_at",
    "url": "url",
}
TEXT_FALLBACKS = ("text", "body", "description", "message", "content", "comment")


def _get(record: dict, dotted: str) -> Any:
    cur: Any = record
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


class _TabularSource(Source):
    def _path(self) -> str:
        return os.path.join(self.base_dir, self.config["path"])

    def _records(self) -> Iterable[dict]:  # pragma: no cover - abstract
        raise NotImplementedError

    def fetch(self) -> Iterable[FeedbackItem]:
        fields = {**DEFAULT_FIELDS, **self.config.get("fields", {})}
        meta_keys = self.config.get("meta", [])
        channel = self.config.get("channel", "other")
        label = os.path.basename(self.config["path"])
        for i, rec in enumerate(self._records(), start=1):
            text = _get(rec, fields["text"])
            if not text:
                text = next((rec[k] for k in TEXT_FALLBACKS if rec.get(k)), None)
            if not text:
                continue
            raw_id = _get(rec, fields["id"]) or i
            yield FeedbackItem(
                id=f"{self.name}-{raw_id}",
                channel=channel,
                source=f"{self.type_name}:{label}",
                text=str(text),
                title=str(_get(rec, fields["title"]) or ""),
                author=str(_get(rec, fields["author"]) or ""),
                created_at=str(_get(rec, fields["created_at"]) or ""),
                url=str(_get(rec, fields["url"]) or ""),
                meta={k: _get(rec, k) for k in meta_keys if _get(rec, k) not in (None, "")},
            )


@register("csv")
class CsvSource(_TabularSource):
    def _records(self) -> Iterable[dict]:
        with open(self._path(), newline="", encoding="utf-8-sig") as fh:
            yield from csv.DictReader(fh)


@register("json")
class JsonSource(_TabularSource):
    """A JSON array, an object with a list under `items_key`, or JSONL."""

    def _records(self) -> Iterable[dict]:
        path = self._path()
        with open(path, encoding="utf-8") as fh:
            if path.endswith(".jsonl"):
                for line in fh:
                    if line.strip():
                        yield json.loads(line)
                return
            data = json.load(fh)
        if isinstance(data, dict):
            data = _get(data, self.config.get("items_key", "items")) or []
        yield from data
