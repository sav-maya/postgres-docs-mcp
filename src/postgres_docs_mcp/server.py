from __future__ import annotations

import json
import logging
import re
from urllib.parse import urljoin

import httpx2
from bs4 import BeautifulSoup
from markdownify import markdownify
from mcp.server import MCPServer

BASE_URL = "https://www.postgresql.org"
DOCS_URL = f"{BASE_URL}/docs"
USER_AGENT = "postgres-docs-mcp/0.1 (+https://github.com/sav-maya/postgres-docs-mcp)"
VERSION_RE = re.compile(r"^(?:current|devel|\d+(?:\.\d+)?)$")
PAGE_RE = re.compile(
    r"^[a-z0-9][a-z0-9._-]*(?:\.html)?(?:#[A-Za-z0-9._:-]+)?$"
)

logger = logging.getLogger(__name__)
mcp = MCPServer("postgres-docs")


def _version(value: str) -> str:
    version = value.strip().lower()
    if not VERSION_RE.fullmatch(version):
        raise ValueError(
            "version must be 'current', 'devel', or a PostgreSQL version such as "
            "'18' or '9.6'"
        )
    return version


def _page(value: str) -> str:
    page = value.strip()
    if not PAGE_RE.fullmatch(page):
        raise ValueError(
            "page must be a documentation slug such as 'sql-select' or "
            "'functions-json.html'"
        )

    name, separator, fragment = page.partition("#")
    if not name.endswith(".html"):
        name += ".html"
    return name + (f"#{fragment}" if separator else "")


async def _get(url: str, **kwargs: object) -> httpx2.Response:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}
    try:
        async with httpx2.AsyncClient(
            follow_redirects=True, headers=headers, timeout=30.0
        ) as client:
            response = await client.get(url, **kwargs)
            response.raise_for_status()
            return response
    except Exception as exc:
        logger.exception("PostgreSQL documentation request failed: %s", url)
        raise RuntimeError("Unable to fetch the PostgreSQL documentation.") from exc


def _version_rows(html: str, status: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, str]] = []

    for row in soup.select("tr"):
        link = row.select_one('a[href^="/docs/"][href$="/index.html"]')
        if not link:
            continue

        match = re.fullmatch(r"/docs/([^/]+)/index\.html", link.get("href", ""))
        if not match:
            continue

        version = match.group(1)
        if version == "current":
            continue

        rows.append(
            {
                "version": version,
                "label": " ".join(row.get_text(" ", strip=True).split()),
                "status": status,
            }
        )

    return rows


def _search_results(
    html: str, version: str, limit: int
) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    prefix = f"{DOCS_URL}/{version}/"
    seen: set[str] = set()
    results: list[dict[str, str]] = []

    for link in soup.find_all("a", href=True):
        url = str(link["href"])
        if not url.startswith(prefix) or url in seen:
            continue

        title = " ".join(link.get_text(" ", strip=True).split())
        if title == url:
            continue

        seen.add(url)
        title = re.sub(r"^PostgreSQL: Documentation: [^:]+:\s*", "", title)
        snippet_node = link.find_next_sibling("div")
        snippet = (
            " ".join(snippet_node.get_text(" ", strip=True).split())
            if snippet_node
            else ""
        )
        results.append(
            {
                "title": title,
                "page": url.rsplit("/", 1)[-1],
                "url": url,
                "snippet": snippet,
            }
        )
        if len(results) == limit:
            break

    return results


def _page_markdown(html: str, page_url: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("#docContent")
    if content is None:
        raise ValueError("The response did not contain PostgreSQL documentation.")

    for node in content.select(".navheader, .navfooter"):
        node.decompose()
    for link in content.find_all("a", href=True):
        link["href"] = urljoin(page_url, str(link["href"]))

    title = soup.title.get_text(" ", strip=True) if soup.title else "PostgreSQL docs"
    title = re.sub(r"^PostgreSQL: Documentation: [^:]+:\s*", "", title)
    body = markdownify(str(content), heading_style="ATX", bullets="-").strip()
    body = re.sub(r"\n{3,}", "\n\n", body)
    return title, body


@mcp.tool()
async def list_versions() -> str:
    """List every PostgreSQL documentation version available online.

    Includes current supported releases, prereleases, the development snapshot,
    and archived unsupported releases.
    """
    current, archive = await _get(f"{DOCS_URL}/"), await _get(
        f"{DOCS_URL}/manuals/archive/"
    )
    versions = _version_rows(current.text, "published")
    versions.extend(_version_rows(archive.text, "archived"))
    return json.dumps({"default": "current", "versions": versions}, indent=2)


@mcp.tool()
async def search_docs(
    query: str, version: str = "current", limit: int = 10
) -> str:
    """Search the official PostgreSQL documentation within one version.

    Args:
        query: Search terms, such as "logical replication conflicts".
        version: "current", "devel", or a published version such as "18" or "9.6".
        limit: Number of results to return, from 1 to 20.
    """
    query = query.strip()
    if not query or len(query) > 200:
        raise ValueError("query must contain between 1 and 200 characters")
    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")

    version = _version(version)
    response = await _get(
        f"{BASE_URL}/search/", params={"q": query, "u": f"/docs/{version}/"}
    )
    results = _search_results(response.text, version, limit)
    return json.dumps(
        {"query": query, "version": version, "results": results}, indent=2
    )


@mcp.tool()
async def get_doc_page(
    page: str,
    version: str = "current",
    offset: int = 0,
    max_chars: int = 30_000,
) -> str:
    """Read one page from the official PostgreSQL documentation as Markdown.

    Use the page slug returned by search_docs. Long pages can be continued by
    calling this tool again with the next offset.

    Args:
        page: Page slug, such as "sql-select" or "functions-json.html".
        version: "current", "devel", or a published version such as "18" or "9.6".
        offset: Character offset at which to start reading.
        max_chars: Maximum characters to return, from 1,000 to 50,000.
    """
    version = _version(version)
    page = _page(page)
    if offset < 0:
        raise ValueError("offset must be zero or greater")
    if not 1_000 <= max_chars <= 50_000:
        raise ValueError("max_chars must be between 1,000 and 50,000")

    page_url = f"{DOCS_URL}/{version}/{page}"
    response = await _get(page_url)
    title, body = _page_markdown(response.text, page_url)
    if offset >= len(body) and body:
        raise ValueError(f"offset exceeds the page length of {len(body)} characters")

    chunk = body[offset : offset + max_chars]
    next_offset = offset + len(chunk)
    truncated = next_offset < len(body)
    metadata = {
        "title": title,
        "version": version,
        "source": page_url,
        "offset": offset,
        "next_offset": next_offset if truncated else None,
        "total_chars": len(body),
    }
    return f"{json.dumps(metadata, indent=2)}\n\n{chunk}"


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
