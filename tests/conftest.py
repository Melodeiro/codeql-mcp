import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from fastmcp import FastMCP, Client
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import mcp, qs
from codeqlclient import CodeQLQueryServer


@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mcp_server():
    """FastMCP server instance for testing"""
    # Just use the main server instance for testing
    return mcp


@pytest.fixture
async def mcp_client(mcp_server):
    """In-memory FastMCP client for testing"""
    async with Client(mcp_server) as client:
        yield client


@pytest.fixture
def mock_codeql_server(mocker):
    """Mock CodeQLQueryServer instance"""
    mock_server = MagicMock(spec=CodeQLQueryServer)
    mock_server.codeql_path = "codeql"
    mock_server.wait_for_completion_callback.return_value = (
        MagicMock(),
        MagicMock(wait=MagicMock()),
        {}
    )
    mock_server.decode_bqrs = MagicMock(return_value='{"results": []}')
    mock_server.find_class_identifier_position = MagicMock(return_value=(1, 1, 1, 10))
    mock_server.find_predicate_identifier_position = MagicMock(return_value=(1, 1, 1, 10))

    mocker.patch('server.qs', mock_server)
    return mock_server


@pytest.fixture
def mock_subprocess(mocker):
    """Mock subprocess.run for external commands"""
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Success",
        stderr=""
    )
    return mock_run


@pytest.fixture
def temp_database(tmp_path):
    """Create a temporary mock CodeQL database"""
    db_path = tmp_path / "test_database"
    db_path.mkdir()

    # Create minimal database structure
    src_zip = db_path / "src.zip"
    src_zip.write_text("mock source archive")

    db_yml = db_path / "codeql-database.yml"
    db_yml.write_text("""
primaryLanguage: python
creationMetadata:
  sha: test123
  cliVersion: 2.15.0
""")

    yield str(db_path)

    # Cleanup
    if db_path.exists():
        shutil.rmtree(db_path)


@pytest.fixture
def temp_query_file(tmp_path):
    """Create a temporary CodeQL query file"""
    query_file = tmp_path / "test_query.ql"
    query_file.write_text("""
import python

class TestClass extends DataFlow::Node {
  TestClass() { this.asExpr() instanceof Name }
}

predicate testPredicate(DataFlow::Node n) {
  n instanceof TestClass
}

from TestClass tc
select tc
""")

    yield str(query_file)


@pytest.fixture
def mock_bqrs_file(tmp_path):
    """Create a mock BQRS file"""
    bqrs_file = tmp_path / "results.bqrs"
    bqrs_file.write_bytes(b"mock bqrs binary content")

    yield str(bqrs_file)


@pytest.fixture
def mock_sarif_result():
    """Mock SARIF analysis result"""
    return {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CodeQL",
                    "version": "2.15.0"
                }
            },
            "results": [{
                "ruleId": "py/sql-injection",
                "level": "error",
                "message": {
                    "text": "SQL injection vulnerability"
                },
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": "test.py"
                        },
                        "region": {
                            "startLine": 10
                        }
                    }
                }]
            }]
        }]
    }


@pytest.fixture
def mock_query_packs():
    """Mock query packs response"""
    return {
        "python": {
            "pack": "codeql/python-queries",
            "suites": [
                "codeql/python-queries:codeql-suites/python-code-scanning.qls",
                "codeql/python-queries:codeql-suites/python-security-extended.qls",
                "codeql/python-queries:codeql-suites/python-security-and-quality.qls"
            ]
        },
        "javascript-typescript": {
            "pack": "codeql/javascript-queries",
            "suites": [
                "codeql/javascript-queries:codeql-suites/javascript-code-scanning.qls",
                "codeql/javascript-queries:codeql-suites/javascript-security-extended.qls",
                "codeql/javascript-queries:codeql-suites/javascript-security-and-quality.qls"
            ]
        }
    }


@pytest.fixture
def mock_security_queries():
    """Mock security queries discovery result"""
    return {
        "sql_injection": [
            {
                "path": "/path/to/codeql/python/ql/src/Security/CWE-089/SqlInjection.ql",
                "language": "python",
                "filename": "SqlInjection.ql"
            }
        ],
        "xss": [
            {
                "path": "/path/to/codeql/python/ql/src/Security/CWE-079/ReflectedXss.ql",
                "language": "python",
                "filename": "ReflectedXss.ql"
            }
        ]
    }


@pytest.fixture
def mock_db_info():
    """Mock database info result"""
    return {
        "path": "/path/to/database",
        "language": "python",
        "lines_of_code": 5000
    }


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset global caches before each test"""
    from tools.database import db_info_cache
    db_info_cache.clear()
    yield