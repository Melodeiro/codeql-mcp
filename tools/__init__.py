"""Tools module: CodeQL MCP tool implementations"""

# Import all tool implementations
from .database import register_database_impl, create_database_impl, get_database_info_impl
from .query import test_predicate_impl, evaluate_query_impl
from .results import decode_bqrs_impl
from .discovery import (
    list_supported_languages_impl,
    list_query_packs_impl,
    discover_queries_impl,
    find_security_queries_impl
)
from .analysis import analyze_database_impl, run_security_scan_impl

__all__ = [
    # Database operations
    'register_database_impl',
    'create_database_impl',
    'get_database_info_impl',
    # Query execution
    'test_predicate_impl',
    'evaluate_query_impl',
    # Results processing
    'decode_bqrs_impl',
    # Discovery
    'list_supported_languages_impl',
    'list_query_packs_impl',
    'discover_queries_impl',
    'find_security_queries_impl',
    # Analysis
    'analyze_database_impl',
    'run_security_scan_impl',
]
