import anyio
import pytest
from mcp import Client

from postgres_docs_mcp.server import (
    _page,
    _page_markdown,
    _search_results,
    _version,
    _version_rows,
    mcp,
)


def test_validates_version_and_page() -> None:
    assert _version("9.6") == "9.6"
    assert _version(" CURRENT ") == "current"
    assert _page("sql-select") == "sql-select.html"
    assert _page("functions-json.html#FUNCTIONS-JSON-CREATION-TABLE") == (
        "functions-json.html#FUNCTIONS-JSON-CREATION-TABLE"
    )

    with pytest.raises(ValueError):
        _version("../about")
    with pytest.raises(ValueError):
        _page("https://example.com")


def test_parses_versions_and_search_results() -> None:
    versions_html = """
    <table>
      <tr><td><a href="/docs/19/index.html">19 beta</a></td></tr>
      <tr><td><a href="/docs/18/index.html">18</a> /
        <a href="/docs/current/index.html">Current</a></td></tr>
    </table>
    """
    assert _version_rows(versions_html, "published") == [
        {"version": "19", "label": "19 beta", "status": "published"},
        {"version": "18", "label": "18 / Current", "status": "published"},
    ]

    search_html = """
    1. <a href="https://www.postgresql.org/docs/18/sql-select.html">
      PostgreSQL: Documentation: 18: SELECT
    </a> [1.0]<br>
    <div>...retrieve rows from a table...</div>
    <a href="https://www.postgresql.org/docs/18/sql-select.html">
      https://www.postgresql.org/docs/18/sql-select.html
    </a>
    """
    assert _search_results(search_html, "18", 10) == [
        {
            "title": "SELECT",
            "page": "sql-select.html",
            "url": "https://www.postgresql.org/docs/18/sql-select.html",
            "snippet": "...retrieve rows from a table...",
        }
    ]


def test_converts_documentation_page_to_markdown() -> None:
    html = """
    <html>
      <head><title>PostgreSQL: Documentation: 18: SELECT</title></head>
      <body>
        <div id="docContent">
          <div class="navheader">Prev Up Next</div>
          <h1>SELECT</h1>
          <p>See <a href="sql-from.html">FROM</a>.</p>
          <div class="navfooter">Prev Up Next</div>
        </div>
      </body>
    </html>
    """
    title, body = _page_markdown(
        html, "https://www.postgresql.org/docs/18/sql-select.html"
    )

    assert title == "SELECT"
    assert "# SELECT" in body
    assert "[FROM](https://www.postgresql.org/docs/18/sql-from.html)" in body
    assert "Prev Up Next" not in body


def test_exposes_expected_mcp_tools() -> None:
    async def check() -> None:
        async with Client(mcp, raise_exceptions=True) as client:
            tools = await client.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "list_versions",
                "search_docs",
                "get_doc_page",
            }

    anyio.run(check)
