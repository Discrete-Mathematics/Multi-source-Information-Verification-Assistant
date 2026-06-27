"""Pluggable evidence sources.

Each adapter implements ``Source`` (async ``search`` -> list[Evidence]).  The
registry below is what the planner routes queries to; adding a new source is a
one-line registration, which is the extensibility story we demo.
"""
from __future__ import annotations

from typing import Dict, List

from .base import Source
from .wikipedia import WikipediaSource
from .arxiv import ArxivSource
from .semantic_scholar import SemanticScholarSource
from .crossref import CrossrefSource
from .web import WebSource

# name -> instance.  Names are what planner.SearchPlan.sources refers to.
REGISTRY: Dict[str, Source] = {
    s.name: s
    for s in [
        WikipediaSource(),
        ArxivSource(),
        SemanticScholarSource(),
        CrossrefSource(),
        WebSource(),
    ]
}

# Logical groups used by the planner to route by claim type.
ACADEMIC_SOURCES: List[str] = ["arxiv", "semantic_scholar", "crossref"]
GENERAL_SOURCES: List[str] = ["wikipedia", "web"]
ALL_SOURCES: List[str] = list(REGISTRY.keys())


def get_source(name: str) -> Source | None:
    return REGISTRY.get(name)
