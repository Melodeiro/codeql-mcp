import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server


class TestRegisterDatabase:
    @pytest.mark.asyncio
    async def test_register_valid_database(self, mcp_client, temp_database, mock_codeql_server):
        """Test registering a valid database"""
        mock_codeql_server.register_databases = MagicMock()

        result = await mcp_client.call_tool(
            "register_database",
            {"db_path": temp_database}
        )

        assert "Database registered" in result.content[0].text
        assert temp_database in result.content[0].text

    @pytest.mark.asyncio
    async def test_register_nonexistent_database(self, mcp_client):
        """Test registering a non-existent database"""
        result = await mcp_client.call_tool(
            "register_database",
            {"db_path": "/nonexistent/path"}
        )

        assert "Database path does not exist" in result.content[0].text

    @pytest.mark.asyncio
    async def test_register_database_missing_src_zip(self, mcp_client, tmp_path):
        """Test registering a database without src.zip"""
        db_path = tmp_path / "incomplete_db"
        db_path.mkdir()

        result = await mcp_client.call_tool(
            "register_database",
            {"db_path": str(db_path)}
        )

        assert "Missing required src.zip" in result.content[0].text


class TestTestPredicate:
    @pytest.mark.asyncio
    async def test_predicate_evaluation(self, mcp_client, temp_query_file, temp_database, mock_codeql_server):
        """Test quick evaluation of a predicate"""
        mock_codeql_server.quick_evaluate_and_wait = MagicMock()

        result = await mcp_client.call_tool(
            "test_predicate",
            {
                "file": temp_query_file,
                "db": temp_database,
                "symbol": "testPredicate"
            }
        )

        assert "/tmp/quickeval.bqrs" in result.content[0].text
        mock_codeql_server.quick_evaluate_and_wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_class_evaluation(self, mcp_client, temp_query_file, temp_database, mock_codeql_server):
        """Test quick evaluation of a class"""
        mock_codeql_server.quick_evaluate_and_wait = MagicMock()

        result = await mcp_client.call_tool(
            "test_predicate",
            {
                "file": temp_query_file,
                "db": temp_database,
                "symbol": "TestClass",
                "output_path": "/custom/output.bqrs"
            }
        )

        assert "/custom/output.bqrs" in result.content[0].text

    @pytest.mark.asyncio
    async def test_predicate_evaluation_error(self, mcp_client, temp_query_file, temp_database, mock_codeql_server):
        """Test handling of evaluation errors"""
        mock_codeql_server.quick_evaluate_and_wait.side_effect = RuntimeError("Evaluation failed")

        result = await mcp_client.call_tool(
            "test_predicate",
            {
                "file": temp_query_file,
                "db": temp_database,
                "symbol": "testPredicate"
            }
        )

        assert "CodeQL evaluation failed" in result.content[0].text


class TestDecodeBqrs:
    @pytest.mark.asyncio
    async def test_decode_bqrs_json(self, mcp_client, mock_bqrs_file, mock_codeql_server):
        """Test decoding BQRS to JSON format"""
        expected_result = '{"results": [{"column": "value"}]}'
        mock_codeql_server.decode_bqrs.return_value = expected_result

        result = await mcp_client.call_tool(
            "decode_bqrs",
            {
                "bqrs_path": mock_bqrs_file,
                "fmt": "json"
            }
        )

        assert expected_result in result.content[0].text
        mock_codeql_server.decode_bqrs.assert_called_with(mock_bqrs_file, "json")

    @pytest.mark.asyncio
    async def test_decode_bqrs_csv(self, mcp_client, mock_bqrs_file, mock_codeql_server):
        """Test decoding BQRS to CSV format"""
        expected_result = "col1,col2\nval1,val2"
        mock_codeql_server.decode_bqrs.return_value = expected_result

        result = await mcp_client.call_tool(
            "decode_bqrs",
            {
                "bqrs_path": mock_bqrs_file,
                "fmt": "csv"
            }
        )

        assert expected_result in result.content[0].text


class TestEvaluateQuery:
    @pytest.mark.asyncio
    @patch('tools.query.validate_query_syntax')
    async def test_evaluate_query_success(self, mock_validate_syntax, mcp_client, temp_query_file, temp_database, mock_codeql_server):
        """Test successful query evaluation"""
        mock_validate_syntax.return_value = {"valid": True, "error": None}
        mock_codeql_server.evaluate_and_wait = MagicMock()

        result = await mcp_client.call_tool(
            "evaluate_query",
            {
                "query_path": temp_query_file,
                "db_path": temp_database
            }
        )

        assert "/tmp/eval.bqrs" in result.content[0].text
        mock_codeql_server.evaluate_and_wait.assert_called_once()

    @pytest.mark.asyncio
    @patch('tools.query.validate_query_syntax')
    async def test_evaluate_query_custom_output(self, mock_validate_syntax, mcp_client, temp_query_file, temp_database, mock_codeql_server):
        """Test query evaluation with custom output path"""
        mock_validate_syntax.return_value = {"valid": True, "error": None}
        custom_path = "/custom/results.bqrs"
        mock_codeql_server.evaluate_and_wait = MagicMock()

        result = await mcp_client.call_tool(
            "evaluate_query",
            {
                "query_path": temp_query_file,
                "db_path": temp_database,
                "output_path": custom_path
            }
        )

        assert custom_path in result.content[0].text

    @pytest.mark.asyncio
    @patch('tools.query.validate_query_syntax')
    async def test_evaluate_query_error(self, mock_validate_syntax, mcp_client, temp_query_file, temp_database, mock_codeql_server):
        """Test handling of evaluation errors"""
        mock_validate_syntax.return_value = {"valid": True, "error": None}
        mock_codeql_server.evaluate_and_wait.side_effect = RuntimeError("Query failed")

        result = await mcp_client.call_tool(
            "evaluate_query",
            {
                "query_path": temp_query_file,
                "db_path": temp_database
            }
        )

        assert "CodeQL evaluation failed" in result.content[0].text


class TestCreateDatabase:
    @pytest.mark.asyncio
    async def test_create_database_basic(self, mcp_client, tmp_path, mock_subprocess):
        """Test basic database creation"""
        source_path = str(tmp_path / "source")
        db_path = str(tmp_path / "database")

        result = await mcp_client.call_tool(
            "create_database",
            {
                "source_path": source_path,
                "language": "python",
                "db_path": db_path
            }
        )

        assert "Database created successfully" in result.content[0].text
        mock_subprocess.assert_called_once()

        # Verify command structure
        cmd = mock_subprocess.call_args[0][0]
        assert "database" in cmd
        assert "create" in cmd
        assert "--language=python" in cmd

    @pytest.mark.asyncio
    async def test_create_database_with_command(self, mcp_client, tmp_path, mock_subprocess):
        """Test database creation with build command"""
        source_path = str(tmp_path / "source")
        db_path = str(tmp_path / "database")

        result = await mcp_client.call_tool(
            "create_database",
            {
                "source_path": source_path,
                "language": "java",
                "db_path": db_path,
                "command": "mvn clean compile"
            }
        )

        assert "Database created successfully" in result.content[0].text
        cmd = mock_subprocess.call_args[0][0]
        assert "--command" in cmd
        assert "mvn clean compile" in cmd

    @pytest.mark.asyncio
    async def test_create_database_overwrite(self, mcp_client, tmp_path, mock_subprocess):
        """Test database creation with overwrite flag"""
        result = await mcp_client.call_tool(
            "create_database",
            {
                "source_path": str(tmp_path),
                "language": "python",
                "db_path": str(tmp_path / "db"),
                "overwrite": True
            }
        )

        cmd = mock_subprocess.call_args[0][0]
        assert "--overwrite" in cmd

    @pytest.mark.asyncio
    async def test_create_database_failure(self, mcp_client, tmp_path, mock_subprocess):
        """Test handling of database creation failure"""
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Build failed"

        result = await mcp_client.call_tool(
            "create_database",
            {
                "source_path": str(tmp_path),
                "language": "python",
                "db_path": str(tmp_path / "db")
            }
        )

        assert "Failed to create database" in result.content[0].text
        assert "Build failed" in result.content[0].text


class TestListSupportedLanguages:
    @pytest.mark.asyncio
    async def test_list_languages_success(self, mcp_client):
        """Test listing supported languages"""
        result = await mcp_client.call_tool(
            "list_supported_languages",
            {}
        )

        languages = [item.text for item in result.content]
        assert "python" in languages
        assert len(languages) > 0

    @pytest.mark.asyncio
    async def test_list_languages_with_codeql_unavailable(self, mcp_client):
        """Test handling when codeql is unavailable"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("codeql not found")
            
            result = await mcp_client.call_tool(
                "list_supported_languages",
                {}
            )
            
            error_text = result.content[0].text
            assert "Error" in error_text or "not found" in error_text


class TestListQueryPacks:
    @pytest.mark.asyncio
    async def test_list_packs_dynamic(self, mcp_client):
        """Test dynamic query pack listing"""
        result = await mcp_client.call_tool(
            "list_query_packs",
            {}
        )

        packs = json.loads(result.content[0].text)
        assert isinstance(packs, dict)
        if "python" in packs:
            assert "pack" in packs["python"]

    @pytest.mark.asyncio
    async def test_list_packs_fallback(self, mcp_client):
        """Test fallback to static pack list on error"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            
            result = await mcp_client.call_tool(
                "list_query_packs",
                {}
            )

            packs = json.loads(result.content[0].text)
            assert "error" in packs
            assert "packs" in packs
            assert "python" in packs["packs"]


class TestDiscoverQueries:
    @pytest.mark.asyncio
    async def test_discover_by_pack(self, mcp_client, mock_subprocess):
        """Test query discovery by pack name"""
        mock_output = {
            "python": [
                "/path/to/SqlInjection.ql",
                "/path/to/XSS.ql"
            ]
        }
        mock_subprocess.return_value.stdout = json.dumps(mock_output)

        result = await mcp_client.call_tool(
            "discover_queries",
            {"pack_name": "codeql/python-queries"}
        )

        # FastMCP returns each list item as separate JSON content
        queries = [json.loads(item.text) for item in result.content]
        assert len(queries) == 2
        assert queries[0]["language"] == "python"
        assert "SqlInjection.ql" in queries[0]["filename"]

    @pytest.mark.asyncio
    async def test_discover_by_language(self, mcp_client, mock_subprocess):
        """Test query discovery by language"""
        mock_output = {
            "javascript": ["/path/to/query.ql"]
        }
        mock_subprocess.return_value.stdout = json.dumps(mock_output)

        result = await mcp_client.call_tool(
            "discover_queries",
            {"language": "javascript"}
        )

        queries = [json.loads(item.text) for item in result.content]
        assert len(queries) == 1

    @pytest.mark.asyncio
    async def test_discover_with_category_filter(self, mcp_client, mock_subprocess):
        """Test query discovery with category filtering"""
        mock_output = {
            "python": [
                "/path/to/security/SqlInjection.ql",
                "/path/to/quality/CodeSmell.ql"
            ]
        }
        mock_subprocess.return_value.stdout = json.dumps(mock_output)

        result = await mcp_client.call_tool(
            "discover_queries",
            {"language": "python", "category": "security"}
        )

        queries = [json.loads(item.text) for item in result.content]
        assert len(queries) == 1
        assert "security" in queries[0]["path"]


class TestFindSecurityQueries:
    @pytest.mark.asyncio
    async def test_find_by_language(self, mcp_client, mock_subprocess):
        """Test finding security queries by language"""
        mock_output = {
            "python": [
                "/path/to/Security/CWE-089/SqlInjection.ql",
                "/path/to/Security/CWE-079/XSS.ql"
            ]
        }
        mock_subprocess.return_value.stdout = json.dumps(mock_output)

        result = await mcp_client.call_tool(
            "find_security_queries",
            {"language": "python"}
        )

        queries = json.loads(result.content[0].text)
        assert "sql_injection" in queries
        assert "xss" in queries

    @pytest.mark.asyncio
    async def test_find_by_vulnerability_type(self, mcp_client, mock_subprocess):
        """Test finding queries for specific vulnerability"""
        mock_output = {
            "python": [
                "/path/to/Security/CWE-089/SqlInjection.ql",
                "/path/to/Security/CWE-079/XSS.ql"
            ]
        }
        mock_subprocess.return_value.stdout = json.dumps(mock_output)

        result = await mcp_client.call_tool(
            "find_security_queries",
            {
                "language": "python",
                "vulnerability_type": "sql_injection"
            }
        )

        queries = json.loads(result.content[0].text)
        assert "sql_injection" in queries
        assert "xss" not in queries

    @pytest.mark.asyncio
    async def test_find_by_database_path(self, mcp_client, mock_subprocess):
        """Test auto-detecting language from database"""
        # Mock database info call
        with patch('server.get_database_info') as mock_db_info:
            mock_db_info.return_value = {
                "language": "python",
                "path": "/path/to/db"
            }

            mock_output = {
                "python": ["/path/to/Security/SqlInjection.ql"]
            }
            mock_subprocess.return_value.stdout = json.dumps(mock_output)

            result = await mcp_client.call_tool(
                "find_security_queries",
                {"db_path": "/path/to/database"}
            )

            queries = json.loads(result.content[0].text)
            assert len(queries) > 0


class TestAnalyzeDatabase:
    @pytest.mark.asyncio
    async def test_analyze_with_query(self, mcp_client, temp_database, mock_subprocess):
        """Test database analysis with single query"""
        result = await mcp_client.call_tool(
            "analyze_database",
            {
                "db_path": temp_database,
                "query_or_suite": "/path/to/query.ql"
            }
        )

        assert "Analysis completed" in result.content[0].text
        assert ".sarif" in result.content[0].text

    @pytest.mark.asyncio
    async def test_analyze_with_suite(self, mcp_client, temp_database, mock_subprocess):
        """Test database analysis with query suite"""
        result = await mcp_client.call_tool(
            "analyze_database",
            {
                "db_path": temp_database,
                "query_or_suite": "codeql-suites/python-security.qls",
                "output_format": "csv",
                "output_path": "/custom/results"
            }
        )

        assert "Analysis completed" in result.content[0].text
        assert "/custom/results.csv" in result.content[0].text

    @pytest.mark.asyncio
    async def test_analyze_failure(self, mcp_client, temp_database, mock_subprocess):
        """Test handling of analysis failure"""
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Analysis error"

        result = await mcp_client.call_tool(
            "analyze_database",
            {
                "db_path": temp_database,
                "query_or_suite": "query.ql"
            }
        )

        assert "Analysis failed" in result.content[0].text


class TestGetDatabaseInfo:
    @pytest.mark.asyncio
    async def test_get_info_success(self, mcp_client, temp_database):
        """Test getting database information"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="primaryLanguage: python\ncreationMetadata:\n  sha: abc123\n  cliVersion: 2.15.0"
            )
            
            result = await mcp_client.call_tool(
                "get_database_info",
                {"db_path": temp_database}
            )

            info = json.loads(result.content[0].text)
            assert "language" in info
            assert info["language"] == "python"
            assert "path" in info

    @pytest.mark.asyncio
    async def test_get_info_with_baseline(self, mcp_client, temp_database, mock_subprocess):
        """Test getting database info with baseline statistics"""
        def side_effect(*args, **kwargs):
            if "resolve" in args[0]:
                return MagicMock(
                    returncode=0,
                    stdout="language: python",
                    stderr=""
                )
            elif "print-baseline" in args[0]:
                return MagicMock(
                    returncode=0,
                    stdout="Database has baseline of 5000 lines",
                    stderr=""
                )
            return MagicMock(returncode=1)

        mock_subprocess.side_effect = side_effect

        result = await mcp_client.call_tool(
            "get_database_info",
            {"db_path": temp_database}
        )

        info = json.loads(result.content[0].text)
        assert info["lines_of_code"] == 5000

    @pytest.mark.asyncio
    async def test_get_info_cached(self, mcp_client, temp_database, mock_subprocess):
        """Test that database info is cached"""
        mock_subprocess.return_value.stdout = "language: python"

        # First call
        await mcp_client.call_tool(
            "get_database_info",
            {"db_path": temp_database}
        )

        # Second call should use cache
        await mcp_client.call_tool(
            "get_database_info",
            {"db_path": temp_database}
        )

        # Should only call subprocess once
        assert mock_subprocess.call_count == 2  # resolve + print-baseline

    @pytest.mark.asyncio
    async def test_get_info_error(self, mcp_client):
        """Test handling of database info errors"""
        result = await mcp_client.call_tool(
            "get_database_info",
            {"db_path": "/nonexistent/database/path"}
        )

        info = json.loads(result.content[0].text)
        assert "error" in info


class TestRunSecurityScan:
    @pytest.mark.asyncio
    async def test_scan_with_language(self, mcp_client, temp_database, mock_subprocess, mock_query_packs):
        """Test security scan with explicit language"""
        with patch('server.list_query_packs') as mock_list_packs:
            mock_list_packs.return_value = mock_query_packs

            result = await mcp_client.call_tool(
                "run_security_scan",
                {
                    "db_path": temp_database,
                    "language": "python"
                }
            )

            assert "Security scan completed" in result.content[0].text
            assert ".sarif" in result.content[0].text

    @pytest.mark.asyncio
    async def test_scan_auto_detect(self, mcp_client, temp_database, mock_subprocess, mock_query_packs):
        """Test security scan with auto-detected language"""
        with patch('server.get_database_info') as mock_db_info:
            mock_db_info.return_value = {"language": "python"}

            with patch('server.list_query_packs') as mock_list_packs:
                mock_list_packs.return_value = mock_query_packs

                result = await mcp_client.call_tool(
                    "run_security_scan",
                    {"db_path": temp_database}
                )

                assert "Security scan completed" in result.content[0].text

    @pytest.mark.asyncio
    async def test_scan_unsupported_language(self, mcp_client, temp_database, mock_query_packs):
        """Test security scan with unsupported language"""
        with patch('server.list_query_packs') as mock_list_packs:
            mock_list_packs.return_value = mock_query_packs

            result = await mcp_client.call_tool(
                "run_security_scan",
                {
                    "db_path": temp_database,
                    "language": "cobol"
                }
            )

            assert "Unsupported language" in result.content[0].text

    @pytest.mark.asyncio
    async def test_scan_failure(self, mcp_client, temp_database, mock_subprocess, mock_query_packs):
        """Test handling of scan failure"""
        with patch('server.list_query_packs') as mock_list_packs:
            mock_list_packs.return_value = mock_query_packs
            mock_subprocess.return_value.returncode = 1
            mock_subprocess.return_value.stderr = "Scan failed"

            result = await mcp_client.call_tool(
                "run_security_scan",
                {
                    "db_path": temp_database,
                    "language": "python"
                }
            )

            assert "Security scan failed" in result.content[0].text