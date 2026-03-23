"""Minimal RSS/Atom feed parser using only the standard library."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RSSEntry:
    title: str
    summary: str
    link: str
    published: str


def parse_rss(xml_text: str, limit: int = 20) -> list[RSSEntry]:
    """Parse an RSS 2.0 or Atom feed and return entries."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        logger.warning("Failed to parse RSS/Atom XML")
        return []

    # Detect feed type
    tag = root.tag.lower()
    if "feed" in tag:
        return _parse_atom(root, limit)
    return _parse_rss2(root, limit)


def _parse_rss2(root: ET.Element, limit: int) -> list[RSSEntry]:
    entries: list[RSSEntry] = []
    for item in root.iter("item"):
        if len(entries) >= limit:
            break
        title = _text(item, "title")
        description = _text(item, "description")
        link = _text(item, "link")
        pub_date = _text(item, "pubDate")
        entries.append(RSSEntry(
            title=title,
            summary=description[:200] if description else "",
            link=link,
            published=pub_date,
        ))
    return entries


def _parse_atom(root: ET.Element, limit: int) -> list[RSSEntry]:
    ns = _atom_ns(root)
    entries: list[RSSEntry] = []
    for entry in root.iter(f"{ns}entry"):
        if len(entries) >= limit:
            break
        title = _text(entry, f"{ns}title")
        summary_el = entry.find(f"{ns}summary")
        if summary_el is None:
            summary_el = entry.find(f"{ns}content")
        summary = (summary_el.text or "")[:200] if summary_el is not None else ""
        link_el = entry.find(f"{ns}link")
        link = link_el.get("href", "") if link_el is not None else ""
        updated = _text(entry, f"{ns}updated") or _text(entry, f"{ns}published")
        entries.append(RSSEntry(
            title=title,
            summary=summary,
            link=link,
            published=updated,
        ))
    return entries


def _atom_ns(root: ET.Element) -> str:
    tag = root.tag
    if tag.startswith("{"):
        return tag[: tag.index("}") + 1]
    return ""


def _text(parent: ET.Element, tag: str) -> str:
    el = parent.find(tag)
    if el is not None and el.text:
        return el.text.strip()
    return ""
