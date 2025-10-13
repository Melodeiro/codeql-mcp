from __future__ import annotations

import os
from typing import Any
from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp.server import FastMCP
from codeqlclient import CodeQLQueryServer

# Import tool implementations
from tools import (
    register_database_impl,
    create_database_impl,
    get_database_info_impl,
    test_predicate_impl,
    evaluate_query_impl,
    decode_bqrs_impl,
    list_supported_languages_impl,
    list_query_packs_impl,
    discover_queries_impl,
    find_security_queries_impl,
    analyze_database_impl,
    run_security_scan_impl,
)


mcp: FastMCP = FastMCP(
    name="CodeQL",
    port=int(os.environ.get("PORT", 8000)),
)
qs: CodeQLQueryServer = CodeQLQueryServer()
qs.start()


@mcp.tool()
async def register_database(db_path: str) -> str:
    """Register a CodeQL database with the query server
    
    Registers a pre-built database with the CodeQL query server for improved 
    performance and resource management across multiple query operations.
    
    Parameters:
    - db_path: Path to database directory (must contain required database files including src.zip)
    
    Prerequisites:
    - Database must be created with create_database() or 'codeql database create' CLI
    
    Workflow:
    1. Validates database structure
    2. Registers in CodeQL query server
    3. Makes available for all query operations
    
    Returns: Confirmation message with database path
    """
    return register_database_impl(qs, db_path)


@mcp.tool()
async def test_predicate(
    file: str, db: str, symbol: str, output_path: str = "/tmp/quickeval.bqrs"
) -> str:
    """Quickly test a single predicate or class from a CodeQL query (10-100x faster than full evaluation)
    
    Evaluates only a specific symbol instead of the entire query. Essential for 
    iterative development and debugging complex queries.
    
    Parameters:
    - file: Path to .ql query file
    - db: Path to CodeQL database
    - symbol: Name of class or predicate to test (e.g., class names, predicate identifiers)
    - output_path: Where to write results (defaults to temporary location)
    
    Use cases:
    - Rapid query development and iteration
    - Testing specific predicates in isolation
    - Debugging data flow analysis
    - Verifying predicate logic before full query run
    
    Workflow:
    1. Validates query file exists
    2. Locates symbol definition in query file
    3. Quick-evaluates only that symbol against database
    4. Writes results to BQRS file
    5. Use decode_bqrs() on returned path to view results
    
    Returns: Path to binary .bqrs result file (decode with decode_bqrs)
    """
    return test_predicate_impl(qs, file, db, symbol, output_path)


@mcp.tool()
async def decode_bqrs(bqrs_path: str, fmt: str) -> str:
    """Convert binary CodeQL query results into readable format
    
    Decodes .bqrs files (Binary Query Result Set) into human/AI-readable formats.
    Essential for analyzing results from evaluate_query() or test_predicate() since 
    BQRS files are binary and cannot be read directly.
    
    Parameters:
    - bqrs_path: Path to .bqrs file (from evaluate_query or test_predicate output)
    - fmt: Output format - choose based on use case:
        * "json" - Structured data, best for programmatic analysis and AI agents
        * "csv" - Tabular format, good for spreadsheets and data export
        * "text" - Human-readable table format
    
    Common workflow:
    1. Run query (returns path to .bqrs file)
    2. Decode results using this tool with desired format
    3. Analyze formatted output
    
    Returns: Query results formatted as string in specified format
    """
    return decode_bqrs_impl(qs, bqrs_path, fmt)


@mcp.tool()
async def evaluate_query(
    query_path: str, db_path: str, output_path: str = "/tmp/eval.bqrs"
) -> str:
    """Execute a complete CodeQL query against a database
    
    Runs a full query file and generates results. This is the standard method 
    for security analysis and comprehensive code scanning.
    
    Parameters:
    - query_path: Path to .ql query file
    - db_path: Path to CodeQL database
    - output_path: Where to write results (defaults to temporary location)
    
    Performance note:
    - Full queries may take seconds to minutes depending on query complexity and codebase size
    - For faster iteration during development, use test_predicate() instead
    
    Prerequisites:
    - Query file must be valid CodeQL syntax with .ql extension
    - Database should be a valid CodeQL database (created with create_database or CLI)
    
    Workflow:
    1. Validates query file exists and syntax
    2. Loads and compiles query
    3. Executes against database
    4. Writes results to binary BQRS file
    5. Use decode_bqrs() on returned path to read results
    
    Returns: Path to binary .bqrs result file (decode with decode_bqrs)
    
    Note: Query is validated before execution to provide fast feedback on syntax errors
    """
    return evaluate_query_impl(qs, query_path, db_path, output_path)


@mcp.tool()
async def create_database(source_path: str, language: str, db_path: str,
                         command: str | None = None, overwrite: bool = False) -> str:
    """Build a CodeQL database from source code
    
    Creates a database by extracting code structure and relationships from your 
    project. Required before running any queries.
    
    Parameters:
    - source_path: Root directory of source code to analyze
    - language: Programming language (use list_supported_languages to see options)
    - db_path: Where to create database directory
    - command: Build command for compiled languages (e.g., build scripts, make targets)
    - overwrite: Whether to replace existing database at db_path
    
    Language types:
    - Interpreted languages: Auto-detected, no build command needed
    - Compiled languages: Require build command to capture compilation
    
    After creation:
    - Use register_database() to make it available for queries
    
    Workflow:
    1. Scans source code in source_path
    2. Extracts code structure and relationships
    3. Creates database at db_path
    4. Register with register_database() before querying
    
    Returns: Success message with created database path
    """
    return create_database_impl(qs, source_path, language, db_path, command, overwrite)


@mcp.tool()
async def list_supported_languages() -> list[str]:
    """List programming languages supported by CodeQL for analysis
    
    Returns available language identifiers that can be used with create_database().
    Language support depends on your CodeQL CLI installation and available extractors.
    
    Language categories:
    - Interpreted languages: Generally auto-detected, no build command needed
    - Compiled languages: Require build command to capture compilation process
    
    Use returned identifiers in create_database(language=...) parameter.
    
    Returns: List of supported language identifiers (dynamically detected from CLI)
    """
    return list_supported_languages_impl(qs)


@mcp.tool()
async def list_query_packs() -> dict[str, Any]:
    """List installed CodeQL query packs available for analysis
    
    Query packs contain pre-written queries for security analysis, code quality,
    and best practices. Each language has its own pack with curated queries.
    
    Pack structure:
    - Each language has dedicated query pack
    - Packs include multiple query suites for different analysis depths
    - Suites vary by purpose: standard scanning, extended security, full analysis
    
    Use with:
    - discover_queries() to list queries in a pack
    - analyze_database() to run pack suites
    
    Returns: Dictionary mapping languages to their query packs and available suites
    """
    return list_query_packs_impl(qs)


@mcp.tool()
async def discover_queries(pack_name: str | None = None, language: str | None = None, category: str | None = None) -> list[str | dict[str, Any]]:
    """Discover available CodeQL queries from installed packs
    
    Lists individual query files available in query packs. Useful for finding
    specific queries to run or understanding pack contents.
    
    Parameters:
    - pack_name: Specific pack identifier (get from list_query_packs)
    - language: Filter by programming language
    - category: Filter by query category (security, quality, etc)
    
    Note: Specify either pack_name OR language, not both
    
    Query organization:
    - Queries grouped by category (Security, Maintainability, Reliability)
    - Further organized by CWE numbers for security queries
    - Each query has unique identifier and description
    
    Use cases:
    - Browse available security queries
    - Find queries for specific vulnerability types
    - Discover code quality checks
    
    Returns: List of query paths and metadata
    """
    return discover_queries_impl(qs, pack_name, language, category)


@mcp.tool()
async def find_security_queries(language: str | None = None, vulnerability_type: str | None = None, db_path: str | None = None) -> dict[str, Any]:
    """Find security-focused CodeQL queries by language and vulnerability type
    
    Searches available query packs for security queries matching specific 
    vulnerability categories. Useful for targeted security analysis.
    
    Parameters:
    - language: Target language (or use db_path to auto-detect)
    - vulnerability_type: Specific category (e.g., injection, xss, etc)
    - db_path: Database path to auto-detect language
    
    Vulnerability categories (use as vulnerability_type parameter):
    - Injection flaws: Various code/command/SQL injection patterns
    - Cross-site scripting: XSS and related issues
    - Path manipulation: Traversal and directory issues
    - Authentication: Credential and session management
    - Data handling: Serialization and XML processing
    - Memory safety: Buffer and bounds issues
    
    Note: Specify either language OR db_path
    
    Returns: Dictionary of vulnerability types mapped to relevant query paths
    """
    return await find_security_queries_impl(qs, get_database_info, discover_queries, 
                                            language, vulnerability_type, db_path)


@mcp.tool()
async def analyze_database(db_path: str, query_or_suite: str, output_format: str = "sarif-latest",
                          output_path: str = "/tmp/analysis") -> str:
    """Run comprehensive analysis on a CodeQL database with query suites
    
    High-level analysis using pre-configured query suites. Generates formatted
    reports suitable for CI/CD integration and GitHub Code Scanning.
    
    Parameters:
    - db_path: Path to CodeQL database
    - query_or_suite: Query suite identifier or path to .qls file
    - output_format: Result format (sarif-latest recommended for GitHub integration)
    - output_path: Base path for output file (extension added automatically)
    
    Output formats:
    - sarif-latest: SARIF format for GitHub Code Scanning (recommended)
    - csv: Comma-separated values for spreadsheet analysis
    
    Query suite types (see list_query_packs for language-specific suites):
    - Standard scanning: Basic security and quality checks
    - Extended security: Comprehensive vulnerability analysis
    - Full analysis: Complete suite including all available checks
    
    Use list_query_packs() to discover available suites for your language.
    
    Returns: Success message with path to generated report file
    """
    return analyze_database_impl(qs, db_path, query_or_suite, output_format, output_path)


@mcp.tool()
async def get_database_info(db_path: str) -> dict[str, Any]:
    """Retrieve metadata about a CodeQL database
    
    Extracts database configuration including programming language, creation time,
    and source location. Useful for verifying database properties before analysis.
    
    Parameters:
    - db_path: Path to database directory
    
    Returned information:
    - Primary language
    - Creation metadata (timestamp, CLI version)
    - Source location prefix
    - Database schema version
    
    Use cases:
    - Verify database language before running queries
    - Check database compatibility
    - Validate database structure
    
    Note: Results are cached for performance
    
    Returns: Dictionary with database metadata
    """
    return get_database_info_impl(qs, db_path)


@mcp.tool()
async def run_security_scan(db_path: str, language: str | None = None, output_path: str = "/tmp/security-scan") -> str:
    """Execute comprehensive security analysis on a codebase
    
    Runs a curated security-focused query suite against the database. This is a
    convenience wrapper that auto-selects appropriate security queries for the language.
    
    Parameters:
    - db_path: Path to CodeQL database
    - language: Target language (auto-detected from database if not specified)
    - output_path: Base path for SARIF output file
    
    What it does:
    1. Detects or validates language
    2. Selects extended security query suite for the language
    3. Runs comprehensive security analysis
    4. Generates SARIF report
    
    Query suite characteristics:
    - Includes high and medium severity security queries
    - Covers major vulnerability categories
    - Extended coverage beyond basic scanning
    
    Use cases:
    - Pre-commit security checks
    - CI/CD security gates
    - Comprehensive vulnerability assessment
    
    Returns: Success message with path to generated SARIF report
    """
    return await run_security_scan_impl(qs, get_database_info, list_query_packs, 
                                        db_path, language, output_path)


if __name__ == "__main__":
    print("Starting CodeQL MCP server...")
    port_env = os.environ.get("PORT", "8000")
    mcp.settings.port = int(port_env) if isinstance(port_env, str) else port_env
    mcp.run("streamable-http")
