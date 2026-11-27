"""Email sources: a folder of .eml files, an .mbox export, or a live IMAP inbox.

Emails are not pre-filtered: the model decides which ones contain a bug or
request and lists the rest under ignored_ids. Use `max_messages` to bound cost.

Config keys:
  eml_dir:  path            folder of .eml files
  mbox:     path            path to an .mbox file (Gmail Takeout, Thunderbird)
  imap:     host, user, folder (default INBOX), since_days (default 14),
            password_env (env var holding the password / app password)
"""

from __future__ import annotations

import datetime as dt
import email
import email.policy
import glob
import imaplib
import mailbox
import os
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from typing import Iterable

from ..models import FeedbackItem
from .base import Source, register


def _body(msg: EmailMessage) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    text = part.get_content()
    if part.get_content_type() == "text/html":
        import re

        text = re.sub(r"<[^>]+>", " ", text)
    # Drop quoted reply history, which mostly repeats earlier messages.
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith(">")]
    return "\n".join(lines).strip()


def _date(msg: EmailMessage) -> str:
    try:
        return parsedate_to_datetime(msg["Date"]).isoformat()
    except Exception:
        return ""


def _to_item(name: str, src: str, key: str, msg: EmailMessage) -> FeedbackItem | None:
    body = _body(msg)
    if not body:
        return None
    return FeedbackItem(
        id=f"{name}-{key}",
        channel="email",
        source=src,
        title=str(msg["Subject"] or ""),
        text=body,
        author=str(msg["From"] or ""),
        created_at=_date(msg),
    )


@register("email")
class EmailSource(Source):
    def fetch(self) -> Iterable[FeedbackItem]:
        limit = int(self.config.get("max_messages", 200))
        count = 0
        for item in self._iter():
            if item is None:
                continue
            yield item
            count += 1
            if count >= limit:
                return

    def _iter(self) -> Iterable[FeedbackItem | None]:
        policy = email.policy.default
        if "eml_dir" in self.config:
            folder = os.path.join(self.base_dir, self.config["eml_dir"])
            for path in sorted(glob.glob(os.path.join(folder, "*.eml"))):
                with open(path, "rb") as fh:
                    msg = email.message_from_binary_file(fh, policy=policy)
                key = os.path.splitext(os.path.basename(path))[0]
                yield _to_item(self.name, f"eml:{os.path.basename(folder)}", key, msg)
        if "mbox" in self.config:
            path = os.path.join(self.base_dir, self.config["mbox"])
            box = mailbox.mbox(path, factory=lambda f: email.message_from_binary_file(f, policy=policy))
            for i, msg in enumerate(box, start=1):
                yield _to_item(self.name, f"mbox:{os.path.basename(path)}", str(i), msg)
        if "imap" in self.config:
            yield from self._imap(self.config["imap"])

    def _imap(self, cfg: dict) -> Iterable[FeedbackItem | None]:
        password = os.environ.get(cfg.get("password_env", "HALKVAKT_IMAP_PASSWORD"), "")
        if not password:
            raise RuntimeError(f"Set {cfg.get('password_env', 'HALKVAKT_IMAP_PASSWORD')} for IMAP source {self.name}")
        since = (dt.date.today() - dt.timedelta(days=int(cfg.get("since_days", 14)))).strftime("%d-%b-%Y")
        conn = imaplib.IMAP4_SSL(cfg["host"], int(cfg.get("port", 993)))
        try:
            conn.login(cfg["user"], password)
            conn.select(cfg.get("folder", "INBOX"), readonly=True)
            _, data = conn.search(None, f'(SINCE "{since}")')
            for num in data[0].split():
                _, parts = conn.fetch(num, "(BODY.PEEK[])")
                raw = parts[0][1]
                msg = email.message_from_bytes(raw, policy=email.policy.default)
                yield _to_item(self.name, f"imap:{cfg['user']}", num.decode(), msg)
        finally:
            try:
                conn.logout()
            except Exception:
                pass
