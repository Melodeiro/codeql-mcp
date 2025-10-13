# CodeQL MCP Server

A Model Context Protocol (MCP) server that wraps the CodeQL CLI and query server, enabling AI agents and tools like [Cursor](https://cursor.sh/) to perform comprehensive code analysis through natural language.

---

## ✨ Features

### Database Management
- Create CodeQL databases from source code
- Register databases with query server
- Retrieve database metadata and statistics

### Query Execution
- Run full CodeQL queries
- Quick-evaluate individual predicates/classes (10-100x faster)
- Decode binary `.bqrs` results to JSON/CSV/text

### Security Analysis
- Discover security queries by language and vulnerability type
- Run comprehensive security scans with pre-configured suites
- Generate SARIF reports for CI/CD integration

### Query Discovery
- List supported languages and query packs
- Discover available queries by category
- Find specific vulnerability detection queries

---

##  Project Structure

```
codeql-mcp/
├── server.py              # MCP server (tool definitions + docstrings)
├── codeqlclient.py        # CodeQL query server client (JSON-RPC)
├── validation.py          # Query validation utilities
├── tools/                 # Modular tool implementations
│   ├── __init__.py        # Exports all tool functions
│   ├── database.py        # Database operations (create, register, info)
│   ├── query.py           # Query execution (evaluate, test predicates)
│   ├── results.py         # Result processing (decode BQRS)
│   ├── discovery.py       # Query/pack discovery (languages, packs, queries)
│   └── analysis.py        # High-level analysis (scan, analyze)
└── tests/                 # Test suite
    ├── conftest.py        # Pytest fixtures
    ├── test_server_tools.py
    ├── test_codeql_client.py
    └── test_integration.py
```

---

## 🚀 Quick Start

### Prerequisites
- [CodeQL CLI](https://github.com/github/codeql-cli-binaries) installed and in your `$PATH`
- Python 3.13+ (managed by `uv`)
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd codeql-mcp

# Install dependencies
uv sync
```

### Running the Server

```bash
# Start MCP server with SSE transport
uv run mcp run server.py:mcp -t sse
```

Server will start at `http://localhost:8000/sse`

### Configuration for Cursor

Add to your `.cursor/config.json`:

```json
{
  "mcpServers": {
    "CodeQL": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## 🛠️ Available MCP Tools

### Database Operations
- `register_database` - Register a CodeQL database with the query server
- `create_database` - Build a CodeQL database from source code
- `get_database_info` - Retrieve database metadata

### Query Execution
- `evaluate_query` - Execute a complete CodeQL query
- `test_predicate` - Quick-evaluate a single predicate/class (fast iteration)
- `decode_bqrs` - Convert binary results to readable format (JSON/CSV/text)

### Discovery
- `list_supported_languages` - List available CodeQL languages
- `list_query_packs` - List installed query packs and suites
- `discover_queries` - Find queries by pack/language/category
- `find_security_queries` - Search security queries by vulnerability type

### Analysis
- `analyze_database` - Run comprehensive analysis with query suites
- `run_security_scan` - Execute security-focused scan with SARIF output

---

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_server_tools.py -v

# Run with coverage
uv run pytest --cov=server --cov=tools --cov=validation
```

---

## 📚 Resources

- [CodeQL Documentation](https://codeql.github.com/docs/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
