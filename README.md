# PostgreSQL Docs MCP

A public, open-source [Model Context Protocol](https://modelcontextprotocol.io/)
server for the official, versioned
[PostgreSQL documentation](https://www.postgresql.org/docs/).

It defaults to the current stable release and can search or read every online
version—including archived, beta, and development documentation.

## Tools

- `list_versions` — list every documentation version available online
- `search_docs` — search within a specific PostgreSQL version
- `get_doc_page` — read a documentation page as Markdown, with pagination for
  long pages

## Access and security

This is a read-only documentation server. It:

- fetches only public pages from `www.postgresql.org`
- never connects to a PostgreSQL database
- does not need credentials, API keys, or environment variables
- cannot execute SQL or modify PostgreSQL projects

## Use it in Cursor

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed,
then add this server to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "postgres-docs": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/sav-maya/postgres-docs-mcp",
        "postgres-docs-mcp"
      ]
    }
  }
}
```

Restart Cursor after saving the file. The first launch downloads the server and
its dependencies. In **Cursor Settings → Tools & MCP**, `postgres-docs` should
appear as enabled with three tools.

Then ask Cursor questions normally. It calls the tools when documentation is
needed. For example:

- `Which PostgreSQL documentation versions are available?`
- `Using the PostgreSQL 18 docs, explain logical replication conflicts.`
- `Look up CREATE PUBLICATION in PostgreSQL 15 and cite the source page.`
- `What changed in the JSON functions between PostgreSQL 16 and 18?`

The version defaults to `current`. Mention a version in your prompt when you
need behavior from a specific release.

## Run locally

Requires Python 3.10+ and uv.

```bash
git clone https://github.com/sav-maya/postgres-docs-mcp.git
cd postgres-docs-mcp
uv sync
uv run postgres-docs-mcp
```

To make Cursor launch the local clone, use an absolute path:

```json
{
  "mcpServers": {
    "postgres-docs": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/postgres-docs-mcp",
        "run",
        "postgres-docs-mcp"
      ]
    }
  }
}
```

The server follows the official
[Build an MCP server](https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server)
guide: Python 3.10+, MCP Python SDK 2.x, typed `@mcp.tool()` functions,
`httpx2`, and stdio transport. It never writes logs to stdout; logs go to
stderr so they cannot corrupt MCP JSON-RPC messages.

## Troubleshooting

- **Server does not appear:** Restart Cursor, then check **Cursor Settings →
  Tools & MCP** for an error beside `postgres-docs`.
- **`uvx` is not found:** Install uv, or replace `"uvx"` in the configuration
  with the absolute path printed by `which uvx` on macOS/Linux or `where uvx`
  on Windows.
- **First launch fails:** Confirm that GitHub and PyPI are reachable. The first
  launch downloads the repository and Python dependencies.
- **A version or page is unavailable:** Call `list_versions` first. PostgreSQL
  publishes unsupported releases in its manual archive, while unreleased
  documentation uses `devel`.
- **Server code looks stale:** Add `"--refresh"` before `"--from"` in the
  `uvx` arguments, then restart Cursor.

## Development

```bash
uv run pytest
```

## Related project

This MCP server provides authoritative, version-specific PostgreSQL reference
material. For curated practitioner guidance on schema design, indexing, query
optimization, and common pitfalls, see
[Postgres Skills](https://github.com/neondatabase/postgres-skills).

```bash
npx skills add neondatabase/postgres-skills
```

## License

[MIT](LICENSE)

This is a community project. It is not affiliated with the PostgreSQL Global
Development Group.
