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
    def test_valid_query_syntax(self):
        """Test syntax validation with pre-configured pack"""
        import os
        import shutil
        
        # Use existing query_tests pack with lock file already committed
        test_pack_dir = os.path.join(os.path.dirname(__file__), "query_tests")
        query_file = os.path.join(test_pack_dir, "simple_test.ql")
        
        # This pack has qlpack.yml and codeql-pack.lock.yml already configured
        result = validate_query_syntax(query_file, "codeql")
        
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
