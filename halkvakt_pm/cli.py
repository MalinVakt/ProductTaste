"""Command line entry point: `python -m halkvakt_pm --config config.toml`."""

from __future__ import annotations

import argparse
import os
import sys
import tomllib

from .models import FeedbackItem
from .report import to_json, to_markdown
from .sources import build_source, known_types
from .triage import DEFAULT_MODEL, triage


def collect(config: dict, base_dir: str) -> list[FeedbackItem]:
    items: list[FeedbackItem] = []
    seen: set[str] = set()
    for src_cfg in config.get("sources", []):
        if src_cfg.get("enabled", True) is False:
            continue
        source = build_source(src_cfg, base_dir=base_dir)
        n = 0
        try:
            for item in source.fetch():
                if item.id in seen:
                    continue
                seen.add(item.id)
                items.append(item)
                n += 1
        except Exception as exc:  # one broken source should not sink the run
            print(f"warning: source {source.name!r} failed: {exc}", file=sys.stderr)
        print(f"  {source.name} ({source.type_name}): {n} items", file=sys.stderr)
    return items


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="halkvakt-pm", description=__doc__)
    p.add_argument("--config", default="config.toml", help="Path to config TOML (default: config.toml)")
    p.add_argument("--out", help="Write the report here (default: stdout)")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p.add_argument("--model", help=f"Claude model (default: {DEFAULT_MODEL})")
    p.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], help="Reasoning effort (default: high)")
    p.add_argument("--limit", type=int, help="Max feedback items sent to the model")
    p.add_argument("--dry-run", action="store_true", help="Collect and print items, do not call Claude")
    args = p.parse_args(argv)

    with open(args.config, "rb") as fh:
        config = tomllib.load(fh)
    base_dir = os.path.dirname(os.path.abspath(args.config))
    product = config.get("product", {})
    name = product.get("name", "Halkvakt")

    print(f"Collecting feedback for {name} (source types: {', '.join(known_types())})", file=sys.stderr)
    items = collect(config, base_dir)
    limit = args.limit or config.get("agent", {}).get("max_items")
    if limit and len(items) > limit:
        print(f"  truncating {len(items)} items to {limit}", file=sys.stderr)
        items = items[:limit]

    if args.dry_run:
        for it in items:
            print(f"{it.id}\t{it.channel}\t{(it.title or it.text)[:90]!r}")
        return 0

    agent_cfg = config.get("agent", {})
    result = triage(
        items,
        product=name,
        product_context=product.get("description", ""),
        extra_guidance=product.get("priorities", ""),
        model=args.model or agent_cfg.get("model", DEFAULT_MODEL),
        effort=args.effort or agent_cfg.get("effort", "high"),
    )
    out = to_json(result) if args.format == "json" else to_markdown(result, items, name)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
