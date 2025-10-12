"""High-level analysis: database analysis and security scanning"""

import subprocess


def analyze_database_impl(qs, db_path: str, query_or_suite: str, output_format: str = "sarif-latest",
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


async def run_security_scan_impl(qs, get_db_info_func, list_packs_func,
                                  db_path: str, language: str = None, 
                                  output_path: str = "/tmp/security-scan") -> str:
    """Implementation for run_security_scan tool
    
    Note: Requires async functions for get_database_info and list_query_packs
    """
    try:
        # Auto-detect language if not provided
        if not language:
            db_info = await get_db_info_func(db_path)
            if "error" in db_info:
                return db_info["error"]
            language = db_info.get("language")
            if not language:
                return "Could not determine language from database"

        # Get the appropriate security suite for the language
        query_packs = await list_packs_func()

        if language not in query_packs:
            return f"Unsupported language: {language}. Supported: {list(query_packs.keys())}"

        # Use the security-extended suite for comprehensive coverage
        suite = query_packs[language]["suites"][1]  # security-extended

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
