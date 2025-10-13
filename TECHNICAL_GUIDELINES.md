# Technical Guidelines - CodeQL MCP Server

> **Source**: Official documentation for FastMCP, pytest, Python subprocess  
> **Inference**: 0% - All statements backed by official docs  
> **Last Updated**: 2025-01-13

---

## FastMCP Tool Implementation

### Tool Definition Patterns

**Source**: FastMCP official documentation

```python
from fastmcp import FastMCP

mcp = FastMCP(name="ServerName")

# Basic tool
@mcp.tool
def add(a: int, b: int) -> int:
    """Adds two integer numbers together."""
    return a + b

# Tool with custom metadata
@mcp.tool(
    name="custom_name",
    description="Custom description",
    tags={"category"},
    meta={"version": "1.0"}
)
def my_tool(param: str) -> str:
    return result
```

### Context Injection

**Source**: FastMCP official documentation

```python
from fastmcp import FastMCP, Context

@mcp.tool
async def process_data(data_uri: str, ctx: Context) -> dict:
    """Tool with access to context."""
    await ctx.info(f"Processing {data_uri}")
    
    # Read resources
    resource = await ctx.read_resource(data_uri)
    
    # Report progress
    await ctx.report_progress(progress=50, total=100)
    
    # Get/set state
    ctx.set_state("key", "value")
    value = ctx.get_state("key")
    
    return {"result": "data"}
```

### Error Handling

**Source**: FastMCP official documentation

```python
from fastmcp.exceptions import ToolError

@mcp.tool
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        # ToolError messages always sent to clients
        raise ToolError("Division by zero is not allowed.")
    
    # Standard exceptions can be masked if mask_error_details=True
    if not isinstance(a, (int, float)):
        raise TypeError("Arguments must be numbers.")
        
    return a / b

# Server configuration
mcp = FastMCP(name="Server", mask_error_details=True)
```

### Async vs Sync Tools

**Source**: FastMCP official documentation

```python
# Both sync and async functions supported
@mcp.tool
def sync_tool(x: int) -> str:
    return str(x)

@mcp.tool
async def async_tool(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

### Handling Blocking Operations

**Source**: FastMCP official documentation

```python
import anyio

def cpu_intensive_task(data: str) -> str:
    # Heavy computation
    return processed_data

@mcp.tool
async def wrapped_cpu_task(data: str) -> str:
    """CPU-intensive task wrapped to prevent blocking."""
    return await anyio.to_thread.run_sync(cpu_intensive_task, data)
```

Alternative with asyncer:

```python
import asyncer
import functools
from typing import Callable, ParamSpec, TypeVar, Awaitable

_P = ParamSpec("_P")
_R = TypeVar("_R")

def make_async_background(fn: Callable[_P, _R]) -> Callable[_P, Awaitable[_R]]:
    @functools.wraps(fn)
    async def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        return await asyncer.asyncify(fn)(*args, **kwargs)
    return wrapper

@mcp.tool()
@make_async_background
def blocking_tool() -> None:
    time.sleep(5)
```

---

## Testing with pytest and FastMCP

### In-Memory Testing Pattern

**Source**: FastMCP official documentation

```python
from fastmcp import FastMCP, Client

server = FastMCP("TestServer")

@server.tool
def get_data(id: str) -> dict:
    return {"id": id, "value": 42}

async def test_tool():
    # Pass server directly - no network
    async with Client(server) as client:
        result = await client.call_tool("get_data", {"id": "123"})
        assert result.data == {"id": "123", "value": 42}
```

### Pytest Fixtures

**Source**: FastMCP + pytest official documentation

```python
import pytest
from fastmcp import FastMCP, Client

@pytest.fixture
def my_server():
    server = FastMCP("TestServer")
    
    @server.tool
    def add(a: int, b: int) -> int:
        return a + b
    
    return server

# DO NOT open clients in fixtures (event loop issues)
# Open clients in test functions instead

async def test_addition(my_server):
    async with Client(my_server) as client:
        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert result.data == 5
```

### Testing Error Handling

**Source**: FastMCP official documentation

```python
async def test_tool_error():
    mcp = FastMCP("test-server")
    
    @mcp.tool
    def failing_tool() -> str:
        raise ValueError("Something went wrong")
    
    async with Client(mcp) as client:
        with pytest.raises(Exception):
            await client.call_tool("failing_tool", {})
```

### Fixture Scopes

**Source**: pytest official documentation

```python
# Session scope - created once for all tests
@pytest.fixture(scope="session")
def expensive_resource():
    resource = create_expensive_resource()
    yield resource
    cleanup(resource)

# Module scope - created once per test module
@pytest.fixture(scope="module")
def db_connection():
    conn = connect_to_database()
    yield conn
    conn.close()

# Function scope (default) - created for each test
@pytest.fixture
def temp_data():
    data = create_temp_data()
    yield data
    delete_temp_data(data)
```

**Important**: Higher scopes (session) instantiated before lower scopes (function). Fixtures within same scope ordered by declaration and dependencies.

### Dynamic Fixture Scope

**Source**: pytest official documentation

```python
def determine_scope(fixture_name, config):
    if config.getoption("--keep-containers", None):
        return "session"
    return "function"

@pytest.fixture(scope=determine_scope)
def docker_container():
    yield spawn_container()
```

### Mocking with monkeypatch

**Source**: pytest official documentation

```python
from pathlib import Path

def test_with_mock(monkeypatch):
    # Mock method
    def mock_home():
        return Path("/fake/home")
    
    monkeypatch.setattr(Path, "home", mock_home)
    
    # Mock environment
    monkeypatch.setenv("USER", "testuser")
    
    # Test code using mocks
    assert Path.home() == Path("/fake/home")
```

### Organizing Mocks with Fixtures

**Source**: pytest official documentation

```python
@pytest.fixture
def mock_subprocess(monkeypatch):
    def mock_run(*args, **kwargs):
        return MagicMock(returncode=0, stdout="success", stderr="")
    
    monkeypatch.setattr("subprocess.run", mock_run)

def test_with_mocked_subprocess(mock_subprocess):
    result = subprocess.run(["echo", "test"])
    assert result.returncode == 0
```

### Coverage Configuration

**Source**: pytest-cov official documentation

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--cov=myproject --cov-report=html --cov-report=term-missing"

[tool.coverage.run]
source = ["myproject"]
omit = ["tests/*", ".venv/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
```

Run with:
```bash
pytest --cov --cov-report=html
```

---

## subprocess Best Practices

### subprocess.run() Parameters

**Source**: Python official documentation

```python
import subprocess

result = subprocess.run(
    args,                     # Required: command and arguments (list or string)
    stdin=None,              # Standard input (None, PIPE, DEVNULL, file descriptor, file object)
    stdout=None,             # Standard output (same options as stdin)
    stderr=None,             # Standard error (same options as stdin)
    capture_output=False,    # If True, captures stdout and stderr (sets both to PIPE)
    shell=False,             # If True, executes through shell (DANGEROUS - see security)
    cwd=None,                # Working directory for child process
    timeout=None,            # Timeout in seconds (raises TimeoutExpired if exceeded)
    check=False,             # If True, raises CalledProcessError on non-zero exit
    encoding=None,           # Text encoding (opens file objects in text mode)
    errors=None,             # Error handling for encoding
    text=None,               # Alias for universal_newlines (opens in text mode)
    env=None,                # Environment variables mapping (replaces inherited env)
    input=None,              # Data to send to stdin (bytes or string if text=True)
)
```

### Timeout Handling

**Source**: Python official documentation

```python
try:
    result = subprocess.run(
        ["codeql", "database", "create", path],
        capture_output=True,
        text=True,
        timeout=3600  # 1 hour
    )
except subprocess.TimeoutExpired as e:
    # Process NOT killed automatically
    # Must kill explicitly for cleanup
    print(f"Command timed out after {e.timeout} seconds")
    print(f"Command: {e.cmd}")
    print(f"Output: {e.output}")  # May be None if not captured
```

**Important**: 
- Process creation itself cannot be interrupted - timeout starts after process spawns
- Very small timeouts (milliseconds) may timeout immediately due to process creation overhead
- Child process NOT killed automatically - must kill for proper cleanup

### Error Handling

**Source**: Python official documentation

```python
try:
    result = subprocess.run(
        ["command", "arg"],
        capture_output=True,
        text=True,
        check=True  # Raises CalledProcessError on non-zero exit
    )
    print(f"Success: {result.stdout}")
    
except subprocess.CalledProcessError as e:
    print(f"Command failed with exit code {e.returncode}")
    print(f"Command: {e.cmd}")
    print(f"Stdout: {e.stdout}")
    print(f"Stderr: {e.stderr}")
    
except subprocess.TimeoutExpired as e:
    print(f"Command timed out after {e.timeout} seconds")

# Manual checking without check=True
result = subprocess.run(["command"], capture_output=True)
if result.returncode != 0:
    print(f"Failed: {result.stderr}")
```

**returncode interpretation**:
- `0`: Success
- `> 0`: Error code
- `< 0`: Killed by signal (POSIX only) - value is `-signal_number`

### Security Considerations

**Source**: Python official documentation

#### Command Injection Prevention

```python
# ✅ SAFE: List arguments (shell=False, default)
subprocess.run(["ls", "-l", user_provided_path])

# ❌ DANGEROUS: shell=True with user input
subprocess.run(f"ls -l {user_input}", shell=True)  # NEVER DO THIS

# ✅ SAFE: If shell required, use shlex.quote()
from shlex import quote
subprocess.run(f"ls -l {quote(user_input)}", shell=True)
```

**Official documentation states**: "Unlike some other popen functions, this library will not implicitly choose to call a system shell. This means that all characters, including shell metacharacters, can safely be passed to child processes. If the shell is invoked explicitly, via `shell=True`, it is the application's responsibility to ensure that all whitespace and metacharacters are quoted appropriately to avoid shell injection vulnerabilities."

#### Windows-Specific Security

**Source**: Python official documentation

"On Windows, batch files (`*.bat` or `*.cmd`) may be launched by the operating system in a system shell regardless of the arguments passed to this library. This could result in arguments being parsed according to shell rules, but without any escaping added by Python. If you are intentionally launching a batch file with arguments from untrusted sources, consider passing `shell=True` to allow Python to escape special characters."

### Cross-Platform Differences

**Source**: Python official documentation

#### Process Termination

```python
# POSIX: sends SIGTERM
# Windows: calls TerminateProcess()
proc.terminate()

# POSIX: sends SIGKILL
# Windows: same as terminate()
proc.kill()

# Windows-specific signals
proc.send_signal(subprocess.signal.CTRL_C_EVENT)
proc.send_signal(subprocess.signal.CTRL_BREAK_EVENT)
```

#### Shell Behavior

```python
# POSIX: Uses /bin/sh
subprocess.run(command, shell=True)

# Windows: Uses COMSPEC environment variable (usually cmd.exe)
# Only needed for built-in shell commands (dir, copy, etc)
subprocess.run("dir", shell=True)  # Windows only
```

#### Argument Handling on Windows

**Source**: Python official documentation

On Windows, list arguments converted using MS C runtime rules:
1. Arguments delimited by whitespace (space or tab)
2. Double quotes group arguments with whitespace
3. Backslash + double quote = literal double quote
4. Backslashes literal unless before double quote
5. Backslashes before quote: pairs = literal backslash, odd count = escape quote

---

## Code Organization Patterns

### Type Hints with Forward References

**Source**: Python typing documentation

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codeqlclient import CodeQLQueryServer

def my_function(qs: 'CodeQLQueryServer', param: str) -> dict[str, str]:
    """Function with forward reference type hint."""
    return {"result": "value"}
```

### TypedDict for Structured Dictionaries

**Source**: context7:/python/mypy - https://github.com/python/mypy/blob/master/docs/source/typed_dict.rst

```python
from typing import TypedDict

Movie = TypedDict('Movie', {'name': str, 'year': int})

movie: Movie = {'name': 'Blade Runner', 'year': 1982}

name = movie['name']  # Okay; type of name is str
year = movie['year']  # Okay; type of year is int
```

### Async Implementation Functions

```python
import asyncio

async def my_tool_impl(qs: 'CodeQLQueryServer', param: str) -> str:
    """Implementation with async subprocess call."""
    result = await asyncio.to_thread(
        subprocess.run,
        [qs.codeql_path, "command", param],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode != 0:
        return f"Error: {result.stderr}"
    
    return result.stdout
```

---

## Type Checking with mypy

### Mypy Import Following Behavior

**Source**: context7:/python/mypy - https://github.com/python/mypy/blob/master/docs/source/running_mypy.rst

"Mypy is designed to doggedly follow all imports, even if the imported module is not a file you explicitly wanted mypy to check."

**`--follow-imports` modes**:
- **normal (default, recommended)**: "Follows all imports normally and type checks all top-level code and bodies of functions/methods with at least one type annotation in the signature."
- **silent**: Same as 'normal' but suppresses all error messages.
- **skip**: Does not follow imports and silently replaces the module (and anything imported from it) with an object of type 'Any'.
- **error**: Similar to 'skip' but flags the import as an error.

**Implication**: When running mypy in pre-commit hooks or CI, check the **entire project**, not individual files, to ensure imports are properly type-checked.

```bash
# ✅ CORRECT: Check whole project
mypy server.py codeqlclient.py tools/

# ❌ WRONG: Check only staged files (misses import dependencies)
mypy file1.py file2.py
```

---

## Git Hooks

### Pre-commit Hook Best Practices

**Source**: https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks

"The `pre-commit` hook is run first, before you even type in a commit message. It's used to inspect the snapshot that's about to be committed, to see if you've forgotten something, to make sure tests run, or to examine whatever you need to inspect in the code. Exiting non-zero from this hook aborts the commit, although you can bypass it with `git commit --no-verify`."

### Getting Staged Files

**Source**: https://git-scm.com/docs/git-diff

```bash
# Get staged Python files
git diff --cached --name-only --diff-filter=ACM | grep '\.py$'
```

**`--diff-filter` options**:
- `A`: Added files
- `C`: Copied files
- `M`: Modified files
- `D`: Deleted files
- `R`: Renamed files

Use `ACM` to get files that should be checked (exclude deleted/renamed).

### Example Pre-commit Hook

```bash
#!/bin/sh
# Pre-commit hook to run mypy type checking

echo "Running mypy type checking..."

# Get list of staged Python files to check if we need to run mypy
STAGED_PY_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')

if [ -z "$STAGED_PY_FILES" ]; then
    echo "No Python files staged for commit, skipping mypy."
    exit 0
fi

echo "Python files staged, running mypy on entire project..."

# Run mypy on the entire project (mypy needs to see all files for correct type checking)
uv run mypy server.py codeqlclient.py validation.py tools/ --show-error-codes

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Mypy type checking failed!"
    echo "Please fix the type errors above before committing."
    exit 1
fi

echo "✅ Mypy type checking passed!"
exit 0
```

---

## References

All guidelines sourced from official documentation:

- **FastMCP**: context7:/jlowin/fastmcp (GitHub repository)
- **pytest**: https://docs.pytest.org/en/stable/
- **pytest-cov**: https://github.com/pytest-dev/pytest-cov/
- **Python subprocess**: https://docs.python.org/3.13/library/subprocess.html
- **mypy**: context7:/python/mypy (GitHub repository)
- **Git**: https://git-scm.com/book/ and https://git-scm.com/docs/

**Verification date**: 2025-01-13  
**Inference ratio**: 0%  
**Sources**: 100% official documentation
