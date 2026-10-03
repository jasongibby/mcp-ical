# Installation and Calendar access

Follow the [README setup](../README.md#installation) to install dependencies and
configure your MCP client. Use absolute paths; if the client cannot find `uv`, use
the path returned by `command -v uv`.

The server requests Calendar access on its first calendar operation, not at import
or startup. It requests full event access on macOS versions that support it and uses
the older access API on earlier versions.

If Calendar access is denied:

1. Open **System Settings → Privacy & Security → Calendars**.
2. Enable access for the application running the server (the MCP client or terminal).
3. Restart that application and retry a calendar tool.

If no permission prompt appears when using Claude Desktop, quit it and try starting
it from Terminal, then invoke a calendar tool:

```bash
/Applications/Claude.app/Contents/MacOS/Claude
```

Application packaging and macOS permissions can affect which application receives
the prompt. Use System Settings to manage access; direct edits to the TCC permission
database are unsupported.

To deliberately reset Claude Desktop's Calendar consent and request it again:

```bash
tccutil reset Calendar com.anthropic.claudefordesktop
```

Restart Claude Desktop after a reset. Permission resets apply to the application,
not just this server.
