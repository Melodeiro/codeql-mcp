"""High-level analysis: database analysis and security scanning"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any
from collections.abc import Callable, Awaitable

if TYPE_CHECKING:
    from codeqlclient import CodeQLQueryServer


def analyze_database_impl(qs: CodeQLQueryServer, db_path: str, query_or_suite: str, output_format: str = "sarif-latest",
                          output_path: str = "/tmp/analysis") -> str:
    """Implementation for analyze_database tool"""
    try:
        # Determine output file extension based on format
        format_extensions = {
            "sarif-latest": ".sarif",
            "csv": ".csv",
            "sarif": ".sarif"
        }

        ext = format_extensions.get(output_format, ".txt")
        full_output_path = f"{output_path}{ext}"

        # Build the command
        cmd = [
            qs.codeql_path, "database", "analyze", db_path,
            query_or_suite,
            f"--format={output_format}",
            f"--output={full_output_path}"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return f"Analysis failed: {result.stderr}"

        return f"Analysis completed. Results saved to: {full_output_path}"

    except Exception as e:
        return f"Error during analysis: {str(e)}"


async def run_security_scan_impl(
    qs: CodeQLQueryServer, 
    get_db_info_func: Callable[[str], Awaitable[dict[str, Any]]], 
    list_packs_func: Callable[[], Awaitable[dict[str, Any]]],
    db_path: str, 
    language: str | None = None, 
    output_path: str = "/tmp/security-scan"
) -> str:
    """Implementation for run_security_scan tool
    
    Note: Requires async functions for get_database_info and list_query_packs
    """
    try:
        # Auto-detect language if not provided
        if not language:
            db_info = await get_db_info_func(db_path)
            error_value = db_info.get("error")
            if error_value is not None:
                return str(error_value)
            language = db_info.get("language")
            if not language:
                return "Could not determine language from database"

        # Get the appropriate security suite for the language
        query_packs = await list_packs_func()

        if language not in query_packs:
            return f"Unsupported language: {language}. Supported: {list(query_packs.keys())}"

        # Use the security-extended suite for comprehensive coverage
        lang_pack_data = query_packs.get(language)
        if not isinstance(lang_pack_data, dict) or "suites" not in lang_pack_data:
            return f"Invalid pack data for language: {language}"
        
        suites = lang_pack_data.get("suites")
        if not isinstance(suites, list) or len(suites) < 2:
            return f"Invalid suites data for language: {language}"
        
        suite_item = suites[1]
        if not isinstance(suite_item, str):
            return f"Invalid suite item for language: {language}"
        
        suite = suite_item  # security-extended

        # Run the query suite
        result = subprocess.run([
            qs.codeql_path, "database", "analyze", db_path,
            suite, "--format=sarif-latest", f"--output={output_path}.sarif"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            return f"Security scan failed: {result.stderr}"

        return f"Security scan completed. Results saved to: {output_path}.sarif"

    except Exception as e:
        return f"Error running security scan: {str(e)}"
