# Halkvakt PM agent

A triage agent for the Halkvakt product. It gathers **bugs**, **social media
comments and requests**, and **emails that contain requests or bugs**, groups
duplicates across channels, and returns **one prioritized list with a written
rationale for each priority**.

```
sources (bug tracker, social, email, ...)  ->  normalise  ->  Claude  ->  ranked Markdown / JSON report
```

## Quick start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...            # or `ant auth login`
cp config.example.toml config.toml      # already points at sample_data/
python -m halkvakt_pm --dry-run         # list collected items, no API call
python -m halkvakt_pm --out reports/triage.md
```

See [`examples/sample_report.md`](examples/sample_report.md) for the shape of the
output.

Options: `--format json`, `--model`, `--effort low|medium|high|xhigh|max`,
`--limit N`, `--config path`.

## What the report contains

- An overview of the state of feedback.
- A table ranked 1..N with priority P0 to P3, type (bug, request, UX, question),
  number of reports, and channels.
- Per issue: what users report, **why it got that priority** (severity, reach,
  urgency, strategic fit and effort, citing the evidence by item ID), a next step,
  and a confidence level.
- The items set aside as spam, praise or off-topic, so nothing disappears silently.

Priority definitions: **P0** fix now (core job broken or severe harm), **P1** this
sprint, **P2** soon, **P3** backlog. Tune the ranking with `product.description`
and `product.priorities` in `config.toml`; the agent applies those as standing
rules.

## Sources

Each `[[sources]]` block in `config.toml` is a plug-in:

| type | Use for | Notes |
|---|---|---|
| `csv` | Exports from any bug tracker (Jira, Linear, Trello, GitHub...) or social tool | Map columns with `fields`, pass extra signals with `meta` |
| `json` | JSON / JSONL exports, e.g. social listening tools | `items_key` for nested lists, dotted keys like `user.handle` |
| `email` | Support inbox | `eml_dir`, `mbox` (Gmail Takeout, Thunderbird), or live `imap` with an app password |
| `github_issues` | GitHub Issues as bug tracker | `repo`, `state`, `labels`; `GITHUB_TOKEN` for private repos |

Add a new source (Linear API, Zendesk, App Store reviews, X API...) by
subclassing `Source` in `halkvakt_pm/sources/`, decorating it with
`@register("name")`, and importing it in `sources/__init__.py`.

## Design

- **A workflow, not an open-ended agent.** Gathering data is deterministic, so
  plain code does it; Claude does the judgment: dedupe across channels, classify,
  rank and explain. That keeps runs cheap, repeatable and easy to audit.
- **One structured call.** Claude Opus 5.5 with adaptive thinking returns a
  validated `TriageResult` (Pydantic schema via structured outputs). Evidence IDs
  the model cites are checked against the real items, and ranks are renumbered.
- **Refusal fallback** is on (`fallbacks: "default"`), so a rare safety-classifier
  decline is retried on Anthropic's recommended fallback model.
- **Feedback is treated as data.** The prompt tells the model never to follow
  instructions inside user feedback.
- **Scheduled runs:** `.github/workflows/triage.yml` runs on demand and has a
  commented weekly schedule. It needs an `ANTHROPIC_API_KEY` repository secret.

## Tests

```bash
pip install pytest && python -m pytest -q
```

Tests run offline with a fake client.
