"""Shared data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

Channel = Literal["bug_tracker", "social", "email", "support", "other"]


@dataclass
class FeedbackItem:
    """One raw piece of feedback, normalised from any source."""

    id: str
    channel: Channel
    source: str  # e.g. "github:owner/repo", "csv:bugs.csv", "imap:support@"
    text: str
    title: str = ""
    author: str = ""
    created_at: str = ""  # ISO 8601 when known
    url: str = ""
    # Free-form signals the source knows about: likes, retweets, comment
    # count, labels, customer plan, etc. Passed through to the model as-is.
    meta: dict = field(default_factory=dict)

    def to_prompt_dict(self, max_chars: int = 2000) -> dict:
        text = self.text if len(self.text) <= max_chars else self.text[:max_chars] + " [...]"
        out = {"id": self.id, "channel": self.channel, "source": self.source, "text": text}
        for key in ("title", "author", "created_at", "url"):
            value = getattr(self, key)
            if value:
                out[key] = value
        if self.meta:
            out["meta"] = self.meta
        return out


# ---- Model output (structured) -------------------------------------------

Priority = Literal["P0", "P1", "P2", "P3"]
Kind = Literal["bug", "feature_request", "ux_issue", "question", "praise", "other"]


class TriagedIssue(BaseModel):
    rank: int = Field(description="1 = do first. Unique, contiguous from 1.")
    priority: Priority
    kind: Kind
    title: str = Field(description="Short, specific title for the issue.")
    summary: str = Field(description="One or two sentences on what users report or ask for.")
    rationale: str = Field(
        description="Why this priority and rank: severity, reach, frequency across "
        "sources, business risk, strategic fit, and rough effort. Cite the evidence."
    )
    evidence_ids: list[str] = Field(description="IDs of the feedback items grouped into this issue.")
    channels: list[Channel] = Field(description="Which channels this issue was seen in.")
    report_count: int = Field(description="Number of distinct feedback items in this issue.")
    suggested_next_step: str = Field(description="Concrete next action for the team.")
    confidence: Literal["high", "medium", "low"] = Field(
        description="How confident the ranking is, given the evidence available."
    )


class TriageResult(BaseModel):
    overview: str = Field(description="3-5 sentence summary of the overall state of feedback.")
    issues: list[TriagedIssue]
    ignored_ids: list[str] = Field(
        description="Feedback items that are spam, off-topic, or have no actionable bug or request."
    )
