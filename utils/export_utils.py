"""Shared helpers for PDF and Word export rendering."""
from __future__ import annotations

import html
import re
import unicodedata

import markdown
from bs4 import BeautifulSoup, NavigableString, Tag


def sanitize_text(text: str) -> str:
    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\u00a0", " ").replace("\u202f", " ")
    normalized = normalized.replace("\u200b", "").replace("\ufeff", "")
    normalized = normalized.replace("\ufffd", "")
    normalized = normalized.replace("▪", "•").replace("‣", "•")
    normalized = normalized.replace("–", "-").replace("—", "-")
    normalized = re.sub(r"[^\S\r\n]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def markdown_soup(markdown_text: str) -> BeautifulSoup:
    safe_markdown = sanitize_text(markdown_text)
    rendered = markdown.markdown(
        safe_markdown,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )
    return BeautifulSoup(f"<div>{rendered}</div>", "html.parser")


def escape_inline_text(text: str) -> str:
    return html.escape(sanitize_text(text))


def inline_html(node) -> str:
    if isinstance(node, NavigableString):
        return escape_inline_text(str(node))
    if not isinstance(node, Tag):
        return ""

    children = "".join(inline_html(child) for child in node.children)
    if node.name in {"strong", "b"}:
        return f"<b>{children}</b>"
    if node.name in {"em", "i"}:
        return f"<i>{children}</i>"
    if node.name == "code":
        return f"<font face='Courier'>{children}</font>"
    if node.name == "a":
        href = html.escape(node.get("href", ""))
        return f"<link href='{href}' color='blue'>{children}</link>"
    if node.name == "br":
        return "<br/>"
    return children


def paragraph_html(tag: Tag) -> str:
    return "".join(inline_html(child) for child in tag.children).strip()


def table_matrix(tag: Tag) -> list[list[str]]:
    rows = []
    for tr in tag.find_all("tr"):
        row = []
        for cell in tr.find_all(["th", "td"]):
            row.append(sanitize_text(cell.get_text(" ", strip=True)))
        if row:
            rows.append(row)
    return rows


def references_table_data(sources: list[dict]) -> list[list[str]]:
    rows = [["#", "Source", "Domain", "URL"]]
    for index, src in enumerate(sources, 1):
        rows.append(
            [
                str(index),
                sanitize_text(src.get("title") or "Untitled Source"),
                sanitize_text(src.get("domain") or ""),
                sanitize_text(src.get("url") or ""),
            ]
        )
    return rows
