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
| `meta` | Instagram and Facebook comments | Comments and replies on recent posts, plus Instagram posts tagging the account; skips Halkvakt's own replies |

### Connecting Halkvakt's live sources

Halkvakt's feedback comes from **Instagram/Facebook** and **Zoho Mail**. Both
blocks are in `config.example.toml` with `enabled = false`; fill them in and
switch them on.

**Zoho Mail (IMAP)**
1. In Zoho Mail: Settings > Mail Accounts > IMAP Access, turn IMAP on.
2. If the account has two-factor sign-in, create an app-specific password
   (Zoho Accounts > Security > App Passwords).
3. Set `user` and the right `host`: `imap.zoho.com` for personal accounts,
   `imappro.zoho.com` for organisation accounts, or the `.eu` variants if the
   account lives in Zoho's EU data centre.
4. `export ZOHO_APP_PASSWORD=...`. The inbox is opened read-only and messages are
   not marked as read.

No IMAP? Export a folder from Zoho Mail as `.eml` files and point `eml_dir` at it.

**Instagram and Facebook (Meta Graph API)**
1. The Instagram account must be a professional (business or creator) account
   linked to Halkvakt's Facebook Page.
2. Create an app at developers.facebook.com, add the Instagram Graph API and
   Facebook Login products.
3. In the Graph API Explorer, generate a User token with `pages_show_list`,
   `pages_read_engagement`, `pages_read_user_content`, `instagram_basic` and
   `instagram_manage_comments`, exchange it for a long-lived token, then call
   `GET /me/accounts` to get the **Page access token** and Page ID.
4. `GET /{page-id}?fields=instagram_business_account` gives the Instagram ID.
5. `export META_ACCESS_TOKEN=<page access token>` and fill in both IDs.

For the GitHub Action, add `META_ACCESS_TOKEN` and `ZOHO_APP_PASSWORD` as
repository secrets.

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
