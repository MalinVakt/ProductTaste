"""Source plug-in interface.

A source is anything that can yield FeedbackItems. To add a new one (Linear,
Jira, Zendesk, X/Twitter, App Store reviews, ...), subclass Source, implement
fetch(), and register it with @register("your-type"). Then reference it from
config.toml with `type = "your-type"`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Iterable

from ..models import FeedbackItem

_REGISTRY: dict[str, type["Source"]] = {}


def register(type_name: str) -> Callable[[type["Source"]], type["Source"]]:
    def deco(cls: type["Source"]) -> type["Source"]:
        _REGISTRY[type_name] = cls
        cls.type_name = type_name
        return cls

    return deco


def build_source(config: dict, base_dir: str = ".") -> "Source":
    type_name = config.get("type")
    if type_name not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY))
        raise ValueError(f"Unknown source type {type_name!r}. Known types: {known}")
    return _REGISTRY[type_name](config, base_dir=base_dir)


def known_types() -> list[str]:
    return sorted(_REGISTRY)


class Source(ABC):
    type_name: str = ""

    def __init__(self, config: dict, base_dir: str = "."):
        self.config = config
        self.base_dir = base_dir
        self.name = config.get("name", self.type_name)

    @abstractmethod
    def fetch(self) -> Iterable[FeedbackItem]:
        """Yield feedback items. Must not raise for individual bad records."""
