"""
Async Scraper Agent — production-grade parallel web scraper.
"""
from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

load_env = __import__("dotenv").load_dotenv
load_env()

_MAX_CONCURRENT = int(os.getenv("MAX_SCRAPE_CONCURRENT", "8"))
_TIMEOUT        = int(os.getenv("SCRAPE_TIMEOUT", "15"))
_MIN_CONTENT    = 200   # minimum characters to consider a scrape successful

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_SKIP_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".zip", ".mp4", ".mp3", ".exe", ".dmg",
}


@dataclass
class ScrapedPage:
    url: str
    title: str
    content: str          # cleaned text
    domain: str
    success: bool
    error: Optional[str] = None


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lstrip("www.")
    except Exception:
        return url


def _should_skip(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _SKIP_EXTENSIONS)


def _extract_text(html: str, url: str) -> tuple[str, str]:
    """Parse HTML → (title, clean text)."""
    soup = BeautifulSoup(html, "lxml")

    # Title
    title_tag = soup.find("title")
    title     = title_tag.get_text(strip=True) if title_tag else _domain(url)

    # Remove noisy tags
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "button", "meta", "noscript",
                     "iframe", "svg", "figure"]):
        tag.decompose()

    # Prefer main content areas
    main = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id=re.compile(r"content|main|article", re.I))
        or soup.find(class_=re.compile(r"content|main|article|post", re.I))
        or soup.body
    )
    raw = main.get_text(separator="\n") if main else soup.get_text(separator="\n")

    # Clean whitespace and encoding
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Strictly handle encoding issues to avoid "unknown character" boxes
    text = text.encode("utf-8", errors="ignore").decode("utf-8")
    # Clean common problematic characters
    text = text.replace("\uFFFD", "").replace("\u00A0", " ")

    return title, text


async def _scrape_one(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    url: str,
) -> ScrapedPage:
    domain = _domain(url)

    if _should_skip(url):
        return ScrapedPage(
            url=url, title="", content="",
            domain=domain, success=False,
            error="Skipped (binary/media file)",
        )

    async with sem:
        try:
            timeout = aiohttp.ClientTimeout(total=_TIMEOUT)
            async with session.get(
                url, headers=_HEADERS, timeout=timeout,
                allow_redirects=True, ssl=False,
            ) as resp:
                if resp.status != 200:
                    return ScrapedPage(
                        url=url, title="", content="",
                        domain=domain, success=False,
                        error=f"HTTP {resp.status}",
                    )
                content_type = resp.headers.get("content-type", "")
                if "text" not in content_type:
                    return ScrapedPage(
                        url=url, title="", content="",
                        domain=domain, success=False,
                        error=f"Non-text content-type: {content_type}",
                    )
                html          = await resp.text(errors="replace")
                title, text   = _extract_text(html, url)

                if len(text) < _MIN_CONTENT:
                    return ScrapedPage(
                        url=url, title=title, content="",
                        domain=domain, success=False,
                        error="Content too short",
                    )

                return ScrapedPage(
                    url=url, title=title,
                    content=text[:50_000],   # cap at 50k chars
                    domain=domain, success=True,
                )
        except asyncio.TimeoutError:
            return ScrapedPage(
                url=url, title="", content="",
                domain=domain, success=False, error="Timeout",
            )
        except Exception as e:
            return ScrapedPage(
                url=url, title="", content="",
                domain=domain, success=False, error=str(e),
            )


async def _scrape_all_async(urls: list[str]) -> list[ScrapedPage]:
    sem = asyncio.Semaphore(_MAX_CONCURRENT)
    connector = aiohttp.TCPConnector(limit=_MAX_CONCURRENT, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks   = [_scrape_one(session, sem, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)


def run_scraper_agent(urls: list[str]) -> list[ScrapedPage]:
    """
    Synchronous entry-point that runs async scraping under the hood.
    Returns a list of ScrapedPage objects (both successes and failures).
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In Streamlit / Jupyter — use nest_asyncio pattern
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(1) as pool:
                future = pool.submit(asyncio.run, _scrape_all_async(urls))
                return future.result()
        else:
            return loop.run_until_complete(_scrape_all_async(urls))
    except RuntimeError:
        return asyncio.run(_scrape_all_async(urls))
