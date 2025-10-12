"""Query validation utilities"""

import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def validate_query_file(query_path: str) -> dict:
    """Validate query file exists and has correct extension
    
    Returns:
        dict: {"valid": bool, "error": str or None}
    """
    query_file = Path(query_path)
    
    if not query_file.exists():
        return {"valid": False, "error": f"Query file not found: {query_path}"}
    
    if query_file.suffix != '.ql':
        return {"valid": False, "error": f"Query file must have .ql extension, got: {query_file.suffix}"}
    
    return {"valid": True, "error": None}


def validate_query_syntax(query_path: str, codeql_path: str, timeout: int = 30) -> dict:
    """Validate CodeQL query syntax using compile --check-only
    
    Args:
        query_path: Path to .ql file
        codeql_path: Path to CodeQL CLI
        timeout: Validation timeout in seconds
    
    Returns:
        dict: {"valid": bool, "error": str or None}
    """
    try:
        result = subprocess.run(
            [codeql_path, "query", "compile", str(query_path), "--check-only"],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            return {"valid": False, "error": f"Query validation failed:\n{error_msg}"}
        
        return {"valid": True, "error": None}
        
    except subprocess.TimeoutExpired:
        return {"valid": False, "error": "Query validation timed out (complex query or system issue)"}
    except FileNotFoundError:
        return {"valid": False, "error": f"CodeQL CLI not found at: {codeql_path}"}
    except Exception as e:
        return {"valid": False, "error": f"Query validation error: {str(e)}"}
