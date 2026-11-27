"""Instagram and Facebook comments via the Meta Graph API.

Reads comments (and replies) on the recent posts of Halkvakt's Facebook Page
and Instagram professional account, plus Instagram posts that tag Halkvakt.
The team's own replies are skipped. Each comment becomes one feedback item,
with the post it was left on passed along as context.

Needs a long-lived Page access token with pages_read_engagement,
pages_read_user_content, instagram_basic and instagram_manage_comments.
See README for how to get one.

Config keys:
  facebook_page_id     Page ID (omit to skip Facebook)
  instagram_user_id    Instagram professional account ID (omit to skip Instagram)
  token_env            env var holding the token (default META_ACCESS_TOKEN)
  max_posts            recent posts to scan per platform (default 25)
  since_days           ignore comments older than this (default 30)
  include_ig_tags      also read posts that tag the account (default true)
  graph_version        default "v23.0"
"""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.parse
import urllib.request
from typing import Iterable, Iterator

from ..models import FeedbackItem
from .base import Source, register


def _parse_time(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00").replace("+0000", "+00:00"))
    except ValueError:
        return None


@register("meta")
class MetaSocialSource(Source):
    def __init__(self, config: dict, base_dir: str = "."):
        super().__init__(config, base_dir)
        self.base = f"https://graph.facebook.com/{config.get('graph_version', 'v23.0')}"
        self.cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=int(config.get("since_days", 30)))
        self.max_posts = int(config.get("max_posts", 25))

    # -- HTTP --------------------------------------------------------------
    def _get(self, path: str, params: dict) -> dict:
        token = os.environ.get(self.config.get("token_env", "META_ACCESS_TOKEN"), "")
        if not token:
            raise RuntimeError(f"Set {self.config.get('token_env', 'META_ACCESS_TOKEN')} for source {self.name}")
        url = path if path.startswith("http") else f"{self.base}/{path}?" + urllib.parse.urlencode(
            {**params, "access_token": token}
        )
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.load(resp)

    def _pages(self, path: str, params: dict, limit: int) -> Iterator[dict]:
        data = self._get(path, params)
        n = 0
        while True:
            for row in data.get("data", []):
                yield row
                n += 1
                if n >= limit:
                    return
            nxt = (data.get("paging") or {}).get("next")
            if not nxt:
                return
            data = self._get(nxt, {})

    def _recent(self, ts: str) -> bool:
        t = _parse_time(ts)
        return t is None or t >= self.cutoff

    # -- Facebook ----------------------------------------------------------
    def _facebook(self, page_id: str) -> Iterable[FeedbackItem]:
        posts = self._pages(
            f"{page_id}/feed", {"fields": "id,message,created_time,permalink_url", "limit": 25}, self.max_posts
        )
        for post in posts:
            comments = self._pages(
                f"{post['id']}/comments",
                {
                    "fields": "id,message,from,created_time,like_count,comment_count,permalink_url",
                    "filter": "stream",  # includes replies
                    "limit": 100,
                },
                500,
            )
            for c in comments:
                author = c.get("from") or {}
                if author.get("id") == page_id or not c.get("message") or not self._recent(c.get("created_time", "")):
                    continue
                yield FeedbackItem(
                    id=f"{self.name}-fb-{c['id']}",
                    channel="social",
                    source=f"facebook:{page_id}",
                    text=c["message"],
                    author=author.get("name", ""),
                    created_at=c.get("created_time", ""),
                    url=c.get("permalink_url", ""),
                    meta={
                        "platform": "facebook",
                        "likes": c.get("like_count", 0),
                        "replies": c.get("comment_count", 0),
                        "on_post": (post.get("message") or "")[:200],
                    },
                )

    # -- Instagram ---------------------------------------------------------
    def _instagram(self, ig_id: str) -> Iterable[FeedbackItem]:
        me = self._get(ig_id, {"fields": "username"}).get("username", "")
        media = self._pages(
            f"{ig_id}/media", {"fields": "id,caption,permalink,timestamp", "limit": 25}, self.max_posts
        )
        for m in media:
            comments = self._pages(
                f"{m['id']}/comments",
                {
                    "fields": "id,text,username,timestamp,like_count,replies{id,text,username,timestamp,like_count}",
                    "limit": 50,
                },
                500,
            )
            for c in comments:
                for row in [c, *((c.get("replies") or {}).get("data", []))]:
                    if row.get("username") == me or not row.get("text") or not self._recent(row.get("timestamp", "")):
                        continue
                    yield FeedbackItem(
                        id=f"{self.name}-ig-{row['id']}",
                        channel="social",
                        source=f"instagram:@{me or ig_id}",
                        text=row["text"],
                        author=row.get("username", ""),
                        created_at=row.get("timestamp", ""),
                        url=m.get("permalink", ""),
                        meta={
                            "platform": "instagram",
                            "likes": row.get("like_count", 0),
                            "on_post": (m.get("caption") or "")[:200],
                        },
                    )
        if self.config.get("include_ig_tags", True):
            tagged = self._pages(
                f"{ig_id}/tags",
                {"fields": "id,caption,username,timestamp,permalink,like_count,comments_count", "limit": 25},
                self.max_posts,
            )
            for t in tagged:
                if not t.get("caption") or not self._recent(t.get("timestamp", "")):
                    continue
                yield FeedbackItem(
                    id=f"{self.name}-igtag-{t['id']}",
                    channel="social",
                    source=f"instagram:@{me or ig_id} (tagged)",
                    text=t["caption"],
                    author=t.get("username", ""),
                    created_at=t.get("timestamp", ""),
                    url=t.get("permalink", ""),
                    meta={"platform": "instagram", "likes": t.get("like_count", 0),
                          "comments": t.get("comments_count", 0), "kind": "post tagging Halkvakt"},
                )

    def fetch(self) -> Iterable[FeedbackItem]:
        if self.config.get("facebook_page_id"):
            yield from self._facebook(str(self.config["facebook_page_id"]))
        if self.config.get("instagram_user_id"):
            yield from self._instagram(str(self.config["instagram_user_id"]))
