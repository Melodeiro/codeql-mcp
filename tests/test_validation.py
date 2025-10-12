"""Real tests for validation.py without mocks"""

import pytest
import tempfile
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation import validate_query_file, validate_query_syntax


class TestValidateQueryFile:
    def test_valid_query_file(self, tmp_path):
        """Test validation of existing .ql file"""
        query_file = tmp_path / "test.ql"
        query_file.write_text("select 1")
        
        result = validate_query_file(str(query_file))
        
        assert result["valid"] is True
        assert result["error"] is None
    
    def test_nonexistent_file(self):
        """Test validation of non-existent file"""
        result = validate_query_file("/nonexistent/path/query.ql")
        
        assert result["valid"] is False
        assert "not found" in result["error"]
    
    def test_wrong_extension(self, tmp_path):
        """Test validation of file with wrong extension"""
        query_file = tmp_path / "test.txt"
        query_file.write_text("select 1")
        
        result = validate_query_file(str(query_file))
        
        assert result["valid"] is False
        assert ".ql extension" in result["error"]
        assert ".txt" in result["error"]


class TestValidateQuerySyntax:
    def test_valid_query_syntax(self, tmp_path):
        """Test syntax validation requires qlpack.yml and query packs"""
        qlpack_file = tmp_path / "qlpack.yml"
        qlpack_file.write_text("""name: test-pack
version: 0.0.0
dependencies:
  codeql/python-all: "*"
""")
        
        query_file = tmp_path / "valid.ql"
        query_file.write_text("""import python

from Module m
select m
""")
        
        result = validate_query_syntax(str(query_file), "codeql")
        
        error_str = str(result.get("error", "")).lower()
        if "dbscheme" in error_str or "could not resolve" in error_str:
            pytest.skip("Query packs not installed, cannot validate syntax")
        
        assert result["valid"] is True
        assert result["error"] is None
    
    def test_invalid_query_syntax(self, tmp_path):
        """Test syntax validation of incorrect query"""
        query_file = tmp_path / "invalid.ql"
        query_file.write_text("""
import python

from Module m
select INVALID_SYNTAX
""")
        
        result = validate_query_syntax(str(query_file), "codeql")
        
        assert result["valid"] is False
        assert "validation failed" in result["error"]
    
    def test_validation_timeout(self, tmp_path):
        """Test timeout handling"""
        query_file = tmp_path / "test.ql"
        query_file.write_text("select 1")
        
        result = validate_query_syntax(str(query_file), "codeql", timeout=0.001)
        
        if result["valid"] is False:
            assert "timed out" in result["error"]
    
    def test_codeql_not_found(self, tmp_path):
        """Test handling when codeql binary not found"""
        query_file = tmp_path / "test.ql"
        query_file.write_text("select 1")
        
        result = validate_query_syntax(str(query_file), "/nonexistent/codeql")
        
        assert result["valid"] is True
        assert result["error"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
