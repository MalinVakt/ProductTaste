"""Built-in sources. Importing this package registers them."""

from . import email_source, files, github_issues, meta_social  # noqa: F401
from .base import Source, build_source, known_types, register

__all__ = ["Source", "build_source", "known_types", "register"]
