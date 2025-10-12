import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server


class TestEndToEndIntegration:
    """End-to-end integration tests that simulate real CodeQL workflows"""

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self, mcp_client, real_test_database):
        """Test complete workflow with real database: register -> info -> query discovery"""

        # Step 1: Register real database
        register_result = await mcp_client.call_tool(
            "register_database",
            {"db_path": real_test_database}
        )
        assert "Database registered" in register_result.content[0].text

        # Step 2: Get database info from real database
        info_result = await mcp_client.call_tool(
            "get_database_info",
            {"db_path": real_test_database}
        )
        info = json.loads(info_result.content[0].text)
        assert info["language"] == "python"
        assert "path" in info

        # Step 3: Discover queries for the language
        discover_result = await mcp_client.call_tool(
            "discover_queries",
            {"language": "python", "category": "security"}
        )
        queries = [json.loads(item.text) for item in discover_result.content]
        assert len(queries) > 0
        assert all(q["language"] == "python" for q in queries)

        # Step 4: Find security queries
        security_result = await mcp_client.call_tool(
            "find_security_queries",
            {"language": "python"}
        )
        security_queries = json.loads(security_result.content[0].text)
        assert isinstance(security_queries, dict)
        assert len(security_queries) > 0

    @pytest.mark.asyncio
    async def test_query_discovery_and_execution(self, mcp_client, tmp_path):
        """Test discovering security queries and executing specific ones"""

        discover_result = await mcp_client.call_tool(
            "discover_queries",
            {"language": "python", "category": "security"}
        )

        queries = [json.loads(item.text) for item in discover_result.content]
        
        assert len(queries) > 0
        assert all("path" in q for q in queries)
        assert all("language" in q for q in queries)
        assert all(q["language"] == "python" for q in queries)
        assert all("security" in q["path"].lower() for q in queries)
        
        # Find SqlInjection.ql - it MUST exist in python-queries pack
        sql_injection_query = next(
            (q for q in queries if "SqlInjection" in q.get("filename", "")), None
        )
        assert sql_injection_query is not None
        assert "path" in sql_injection_query
        assert "language" in sql_injection_query

        security_result = await mcp_client.call_tool(
            "find_security_queries",
            {"language": "python", "vulnerability_type": "sql_injection"}
        )

        security_queries = json.loads(security_result.content[0].text)
        assert isinstance(security_queries, dict)
        assert "sql_injection" in security_queries
        assert isinstance(security_queries["sql_injection"], list)
        assert len(security_queries["sql_injection"]) > 0

    @pytest.mark.asyncio
    async def test_multi_language_support(self, mcp_client):
        """Test support for multiple programming languages"""

        languages_result = await mcp_client.call_tool(
            "list_supported_languages",
            {}
        )

        languages = [item.text for item in languages_result.content]
        assert "python" in languages
        assert "javascript" in languages
        assert "java" in languages

        packs_result = await mcp_client.call_tool(
            "list_query_packs",
            {}
        )

        packs = json.loads(packs_result.content[0].text)
        assert isinstance(packs, dict)

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, mcp_client, tmp_path, mock_subprocess):
        """Test error handling in various scenarios"""

        # Test database creation failure - use real error message
        mock_subprocess.return_value = MagicMock(
            returncode=1,
            stderr="Error: Could not process source code"
        )

        create_error_result = await mcp_client.call_tool(
            "create_database",
            {
                "source_path": str(tmp_path),
                "language": "python",
                "db_path": str(tmp_path / "failed_db")
            }
        )
        assert "Failed to create database" in create_error_result.content[0].text

        # Test analysis failure - use real error message
        mock_subprocess.return_value = MagicMock(
            returncode=1,
            stderr="Error: Could not find query suite"
        )

        analysis_error_result = await mcp_client.call_tool(
            "analyze_database",
            {
                "db_path": str(tmp_path / "nonexistent"),
                "query_or_suite": "invalid-suite.qls"
            }
        )
        assert "Analysis failed" in analysis_error_result.content[0].text

        # Test invalid database registration - this is REAL behavior, no mocks needed
        register_error_result = await mcp_client.call_tool(
            "register_database",
            {"db_path": "/completely/nonexistent/path"}
        )
        assert "Database path does not exist" in register_error_result.content[0].text

    @pytest.mark.asyncio
    async def test_caching_behavior(self, mcp_client, real_test_database):
        """Test that caching works correctly for database info"""
        from tools.database import db_info_cache
        
        initial_cache_size = len(db_info_cache)
        
        # First call - should populate cache
        info_result1 = await mcp_client.call_tool(
            "get_database_info",
            {"db_path": real_test_database}
        )
        info1 = json.loads(info_result1.content[0].text)

        # Second call - should use cache
        info_result2 = await mcp_client.call_tool(
            "get_database_info",
            {"db_path": real_test_database}
        )
        info2 = json.loads(info_result2.content[0].text)

        assert info1 == info2
        assert len(db_info_cache) > initial_cache_size
        assert real_test_database in str(db_info_cache) or Path(real_test_database).resolve() in [Path(k) for k in db_info_cache.keys()]

    @pytest.mark.asyncio
    async def test_vulnerability_pattern_matching(self, mcp_client):
        """Test that vulnerability pattern matching works with real CodeQL data"""

        # Test finding all security queries for python
        all_security_result = await mcp_client.call_tool(
            "find_security_queries",
            {"language": "python"}
        )

        all_security = json.loads(all_security_result.content[0].text)
        
        # Verify structure
        assert isinstance(all_security, dict)
        assert len(all_security) > 0
        
        # Real CodeQL python-queries pack MUST have these core vulnerabilities
        # These are confirmed to exist in codeql/python-queries 1.6.6
        required_vulns = ["sql_injection", "xss", "command_injection", "path_traversal", 
                         "deserialization", "xxe", "ldap_injection", "code_injection"]
        for vuln in required_vulns:
            assert vuln in all_security, f"Missing {vuln} in security queries"
        
        # Verify each category has actual queries
        for vuln_type, queries in all_security.items():
            assert isinstance(queries, list), f"{vuln_type} should be a list"
            assert len(queries) > 0, f"{vuln_type} should have queries"
            for query in queries:
                assert "path" in query
                assert "language" in query
                assert query["language"] == "python"
                # Verify path contains security indicator
                assert "security" in query["path"].lower() or "cwe-" in query["path"].lower()

        # Test finding specific vulnerability type
        sql_only_result = await mcp_client.call_tool(
            "find_security_queries",
            {"language": "python", "vulnerability_type": "sql_injection"}
        )

        sql_only = json.loads(sql_only_result.content[0].text)
        assert "sql_injection" in sql_only
        assert "xss" not in sql_only
        assert len(sql_only) == 1
        assert len(sql_only["sql_injection"]) >= 1
        # Verify it's the actual SqlInjection.ql query
        assert any("SqlInjection" in q["path"] for q in sql_only["sql_injection"])

    @pytest.mark.asyncio
    async def test_real_file_operations(self, tmp_path):
        """Test operations with real temporary files"""

        # Create a real query file
        query_file = tmp_path / "real_test.ql"
        query_content = '''
import python

class TestClass extends Expr {
    TestClass() { this.isCall() }
}

predicate testPredicate(Call c) {
    c instanceof TestClass
}

from TestClass tc
select tc
'''
        query_file.write_text(query_content)

        # Test position finding with real file
        from codeqlclient import CodeQLQueryServer

        server = CodeQLQueryServer()

        # Find class position
        start_line, start_col, end_line, end_col = server.find_class_identifier_position(
            str(query_file), "TestClass"
        )
        assert start_line == 4  # Line with class definition
        assert start_col > 0
        assert end_col > start_col

        # Find predicate position
        start_line, start_col, end_line, end_col = server.find_predicate_identifier_position(
            str(query_file), "testPredicate"
        )
        assert start_line == 8  # Line with predicate definition
        assert start_col > 0

        # Test with non-existent symbols
        with pytest.raises(ValueError, match="Class name 'NonExistent' not found"):
            server.find_class_identifier_position(str(query_file), "NonExistent")

        with pytest.raises(ValueError, match="Predicate name 'nonExistent' not found"):
            server.find_predicate_identifier_position(str(query_file), "nonExistent")


class TestPerformanceAndScaling:
    """Test performance characteristics and scaling behavior"""

    @pytest.mark.asyncio
    async def test_large_query_list_handling(self, mcp_client):
        """Test handling of large numbers of queries"""

        discover_result = await mcp_client.call_tool(
            "discover_queries",
            {"language": "python"}
        )

        queries = [json.loads(item.text) for item in discover_result.content]

        assert len(queries) > 0
        
        for query in queries[:10]:
            assert "path" in query
            assert "language" in query
            assert "filename" in query

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, mcp_client):
        """Test behavior under concurrent tool calls"""
        import asyncio

        tasks = []
        for i in range(5):
            task = mcp_client.call_tool("list_supported_languages", {})
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            languages = [item.text for item in result.content]
            assert "python" in languages

    @pytest.mark.asyncio
    async def test_memory_cleanup(self, mcp_client, real_test_database):
        """Test that memory is properly cleaned up"""

        # This test ensures that caches are properly managed
        # and don't grow unbounded

        from tools.database import db_info_cache
        initial_cache_size = len(db_info_cache)

        # Call get_database_info multiple times on same database
        # Should use cache, not grow unbounded
        for i in range(10):
            await mcp_client.call_tool(
                "get_database_info",
                {"db_path": real_test_database}
            )

        # Cache should have grown by exactly 1 entry (same database)
        final_cache_size = len(db_info_cache)
        assert final_cache_size == initial_cache_size + 1