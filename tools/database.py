"""Database operations: creation, registration, and metadata retrieval"""

import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Cache for database info to avoid repeated calls
db_info_cache = {}


def register_database_impl(qs, db_path: str) -> str:
    """Implementation for register_database tool"""
    db_path_resolved = Path(db_path).resolve()
    if not db_path_resolved.exists():
        return f"Database path does not exist: {db_path}"

    source_zip = db_path_resolved / "src.zip"
    if not source_zip.exists():
        return f"Missing required src.zip in: {db_path}"

    db_entry = {
        "uri": Path(db_path).resolve().as_uri(),
        "content": {
            "sourceArchiveZip": (Path(db_path) / "src.zip").resolve().as_uri(),
            "dbDir": Path(db_path).resolve().as_uri(),
        },
    }
    callback, done, result_holder = qs.wait_for_completion_callback()
    qs.register_databases(
        [db_path],
        callback=callback,
        progress_callback=lambda msg: logger.debug("register progress: %s", msg),
    )
    done.wait()
    return f"Database registered: {db_path}"


def create_database_impl(qs, source_path: str, language: str, db_path: str,
                         command: str = None, overwrite: bool = False) -> str:
    """Implementation for create_database tool"""
    try:
        # Build the command
        cmd = [qs.codeql_path, "database", "create", db_path, f"--language={language}"]

        if command:
            cmd.extend(["--command", command])

        if overwrite:
            cmd.append("--overwrite")

        # Add source root if provided
        if source_path:
            cmd.extend(["--source-root", source_path])

        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=source_path or ".")

        if result.returncode != 0:
            return f"Failed to create database: {result.stderr}"

        return f"Database created successfully at: {db_path}"

    except Exception as e:
        return f"Error creating database: {str(e)}"


def get_database_info_impl(qs, db_path: str) -> dict:
    """Implementation for get_database_info tool"""
    global db_info_cache

    try:
        db_path_str = str(Path(db_path).resolve())

        # Check cache first
        if db_path_str in db_info_cache:
            return db_info_cache[db_path_str]

        # Use official codeql resolve database command
        result = subprocess.run(
            [qs.codeql_path, "resolve", "database", db_path],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            return {"error": f"Failed to get database info: {result.stderr}"}

        # Parse JSON output from codeql resolve database
        import json
        db_data = json.loads(result.stdout)
        
        # Extract language from languages array
        # codeql resolve database ALWAYS returns JSON with "languages": [...]
        language = None
        if "languages" in db_data and isinstance(db_data["languages"], list):
            language = db_data["languages"][0] if db_data["languages"] else None
        
        info = {
            "path": db_path_str,
            "language": language
        }

        # Get baseline info for statistics
        baseline_result = subprocess.run(
            [qs.codeql_path, "database", "print-baseline", "--", db_path],
            capture_output=True, text=True
        )

        if baseline_result.returncode == 0:
            import re
            for line in baseline_result.stdout.split('\n'):
                if 'baseline of' in line and 'lines' in line:
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        info['lines_of_code'] = int(numbers[0])

        # Cache the result
        db_info_cache[db_path_str] = info
        return info

    except Exception as e:
        return {"error": f"Error getting database info: {str(e)}"}
