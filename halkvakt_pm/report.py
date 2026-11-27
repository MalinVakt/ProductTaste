"""Render a TriageResult as Markdown (for humans) or JSON (for tools)."""

from __future__ import annotations

import datetime as dt
from typing import Sequence

from .models import FeedbackItem, TriageResult

KIND_LABEL = {
    "bug": "Bug",
    "feature_request": "Request",
    "ux_issue": "UX",
    "question": "Question",
    "praise": "Praise",
    "other": "Other",
}


def to_markdown(result: TriageResult, items: Sequence[FeedbackItem], product: str = "Halkvakt") -> str:
    by_id = {it.id: it for it in items}
    today = dt.date.today().isoformat()
    channels = sorted({it.channel for it in items})
    lines = [
        f"# {product} feedback triage, {today}",
        "",
        f"{len(items)} items from {', '.join(channels) or 'no sources'}; "
        f"{len(result.issues)} issues, {len(result.ignored_ids)} items set aside.",
        "",
        "## Overview",
        "",
        result.overview,
        "",
        "## Priority list",
        "",
        "| # | Priority | Type | Issue | Reports | Channels |",
        "|---|---|---|---|---|---|",
    ]
    for i in result.issues:
        lines.append(
            f"| {i.rank} | {i.priority} | {KIND_LABEL[i.kind]} | {i.title} | {i.report_count} | {', '.join(i.channels)} |"
        )
    lines += ["", "## Rationale", ""]
    for i in result.issues:
        lines += [
            f"### {i.rank}. [{i.priority}] {i.title}",
            "",
            f"**What:** {i.summary}",
            "",
            f"**Why {i.priority}:** {i.rationale}",
            "",
            f"**Next step:** {i.suggested_next_step}",
            "",
            f"**Confidence:** {i.confidence}",
            "",
            "**Evidence:**",
        ]
        for eid in i.evidence_ids:
            it = by_id.get(eid)
            if not it:
                continue
            label = it.title or it.text[:80].replace("\n", " ")
            link = f" ([link]({it.url}))" if it.url else ""
            lines.append(f"- `{eid}` ({it.channel}) {label}{link}")
        lines.append("")
    if result.ignored_ids:
        lines += ["## Set aside", "", ", ".join(f"`{x}`" for x in result.ignored_ids), ""]
    return "\n".join(lines)


def to_json(result: TriageResult) -> str:
    return result.model_dump_json(indent=2)
