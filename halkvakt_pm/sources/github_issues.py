"""GitHub Issues as a bug tracker source.

Config keys:
  repo          owner/name
  state         open | closed | all (default open)
  labels        optional comma-separated label filter
  max_issues    default 100
  token_env     env var with a GitHub token (default GITHUB_TOKEN); optional
                for public repos
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Iterable

from ..models import FeedbackItem
from .base import Source, register


@register("github_issues")
class GitHubIssuesSource(Source):
    API = "https://api.github.com"

    def _get(self, url: str) -> list:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
        token = os.environ.get(self.config.get("token_env", "GITHUB_TOKEN"))
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    def fetch(self) -> Iterable[FeedbackItem]:
        repo = self.config["repo"]
        limit = int(self.config.get("max_issues", 100))
        params = f"state={self.config.get('state', 'open')}&per_page=100"
        if self.config.get("labels"):
            params += f"&labels={self.config['labels']}"
        seen = 0
        page = 1
        while seen < limit:
            batch = self._get(f"{self.API}/repos/{repo}/issues?{params}&page={page}")
            if not batch:
                return
            for issue in batch:
                if "pull_request" in issue:
                    continue
                yield FeedbackItem(
                    id=f"{self.name}-{issue['number']}",
                    channel="bug_tracker",
                    source=f"github:{repo}",
                    title=issue["title"],
                    text=issue.get("body") or issue["title"],
                    author=(issue.get("user") or {}).get("login", ""),
                    created_at=issue.get("created_at", ""),
                    url=issue.get("html_url", ""),
                    meta={
                        "labels": [lb["name"] for lb in issue.get("labels", [])],
                        "comments": issue.get("comments", 0),
                        "reactions": (issue.get("reactions") or {}).get("total_count", 0),
                        "state": issue.get("state"),
                    },
                )
                seen += 1
                if seen >= limit:
                    return
            page += 1
