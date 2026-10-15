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

## Add to Cursor

Add this server to `~/.cursor/mcp.json`:

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

Restart Cursor after saving the configuration. The first launch downloads the
server and its dependencies.

## Run locally

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/sav-maya/postgres-docs-mcp.git
cd postgres-docs-mcp
uv sync
uv run postgres-docs-mcp
```

The server uses stdio. Logs go to stderr so they do not interfere with MCP
messages.

## Development

```bash
uv run pytest
```

## License

[MIT](LICENSE)

This is a community project. It is not affiliated with the PostgreSQL Global
Development Group.
