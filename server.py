import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp.server import FastMCP
from codeqlclient import CodeQLQueryServer
from pathlib import Path
import json


mcp = FastMCP(
    name="CodeQL",
    port=os.environ.get("PORT", 8000),
)
qs = CodeQLQueryServer()
qs.start()

# Cache for database info to avoid repeated calls
db_info_cache = {}


@mcp.tool()
async def register_database(db_path: str) -> str:
    """This tool registers a CodeQL database given a path"""
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
        progress_callback=lambda msg: print("[progress] register:", msg),
    )
    done.wait()
    return f"Database registered: {db_path}"


@mcp.tool()
async def test_predicate(
    file: str, db: str, symbol: str, output_path: str = "/tmp/quickeval.bqrs"
) -> str:
    """Tests a specific predicate or class in CodeQL query (10-100x faster than full query). Useful for debugging during query development"""
    try:
        start, scol, end, ecol = qs.find_class_identifier_position(file, symbol)
    except ValueError:
        start, scol, end, ecol = qs.find_predicate_identifier_position(
            file, symbol
        )
    try:
        qs.quick_evaluate_and_wait(
            file, db, output_path, start, scol, end, ecol
        )
    except RuntimeError as re:
        return f"CodeQL evaluation failed: {re}"
    return output_path


@mcp.tool()
async def decode_bqrs(bqrs_path: str, fmt: str) -> str:
    """This can be used to decode CodeQL results, format is either csv for problem queries or json for path-problems"""
    return qs.decode_bqrs(bqrs_path, fmt)


@mcp.tool()
async def evaluate_query(
    query_path: str, db_path: str, output_path: str = "/tmp/eval.bqrs"
) -> str:
    """Runs a CodeQL query on a given database"""
    try:
        qs.evaluate_and_wait(query_path, db_path, output_path)
    except RuntimeError as re:
        return f"CodeQL evaluation failed: {re}"
    return output_path


# Removed find_class_position and find_predicate_position - used internally by test_predicate only


@mcp.tool()
async def create_database(source_path: str, language: str, db_path: str,
                         command: str = None, overwrite: bool = False) -> str:
    """Creates a CodeQL database from source code"""
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


@mcp.tool()
async def list_supported_languages() -> list:
    """Lists CodeQL supported languages for database creation"""
    try:
        result = subprocess.run([qs.codeql_path, "resolve", "languages"],
                              capture_output=True, text=True)

        if result.returncode != 0:
            return ["Error getting languages: " + result.stderr]

        # Parse the output to extract language names
        languages = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                # Extract language name from the output format
                lang = line.strip().split()[0] if line.strip().split() else line.strip()
                languages.append(lang)

        return languages

    except Exception as e:
        return [f"Error: {str(e)}"]


@mcp.tool()
async def list_query_packs() -> dict:
    """Dynamically lists installed CodeQL query packs"""
    try:
        # Get installed packs using codeql resolve packs
        result = subprocess.run(
            [qs.codeql_path, "resolve", "packs", "--kind=query"],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            # Fallback to static list if command fails
            return {
                "error": "Could not dynamically list packs, using defaults",
                "packs": {
                    "python": "codeql/python-queries",
                    "javascript": "codeql/javascript-queries",
                    "java": "codeql/java-queries",
                    "csharp": "codeql/csharp-queries",
                    "cpp": "codeql/cpp-queries",
                    "go": "codeql/go-queries",
                    "ruby": "codeql/ruby-queries"
                }
            }

        # Parse the output to extract pack information
        packs_by_language = {}
        lines = result.stdout.strip().split('\n')

        for line in lines:
            if 'codeql/' in line and '-queries' in line:
                # Extract pack name from the line
                parts = line.strip().split()
                for part in parts:
                    if 'codeql/' in part and '-queries' in part:
                        pack_name = part.split('(')[0].strip()
                        # Extract language from pack name
                        lang = pack_name.replace('codeql/', '').replace('-queries', '')

                        # Map to standard language names
                        lang_map = {
                            'javascript': 'javascript-typescript',
                            'java': 'java-kotlin',
                            'cpp': 'c-cpp'
                        }
                        display_lang = lang_map.get(lang, lang)

                        packs_by_language[display_lang] = {
                            "pack": pack_name,
                            "suites": [
                                f"{pack_name}:codeql-suites/{lang}-code-scanning.qls",
                                f"{pack_name}:codeql-suites/{lang}-security-extended.qls",
                                f"{pack_name}:codeql-suites/{lang}-security-and-quality.qls"
                            ]
                        }
                        break

        return packs_by_language if packs_by_language else {
            "message": "No query packs found. Install CodeQL packs first."
        }

    except Exception as e:
        return {"error": f"Error listing packs: {str(e)}"}


@mcp.tool()
async def discover_queries(pack_name: str = None, language: str = None, category: str = None) -> list:
    """Dynamically discovers available CodeQL queries from packs. Either pack_name or language should be specified"""
    try:
        cmd = [qs.codeql_path, "resolve", "queries", "--format=bylanguage"]

        if pack_name:
            cmd.append(pack_name)
        elif language:
            # Use standard pack for language
            lang_packs = {
                "python": "codeql/python-queries",
                "javascript": "codeql/javascript-queries",
                "typescript": "codeql/javascript-queries",
                "java": "codeql/java-queries",
                "kotlin": "codeql/java-queries",
                "csharp": "codeql/csharp-queries",
                "cpp": "codeql/cpp-queries",
                "c": "codeql/cpp-queries",
                "go": "codeql/go-queries",
                "ruby": "codeql/ruby-queries",
                "swift": "codeql/swift-queries",
                "rust": "codeql/rust-queries"
            }
            if language.lower() in lang_packs:
                cmd.append(lang_packs[language.lower()])
            else:
                return [f"Unsupported language: {language}"]
        else:
            return [f"Error: specify either language or pack name"]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return [f"Error discovering queries: {result.stderr}"]

        import json
        data = json.loads(result.stdout)

        queries = []
        for extractor, query_list in data.items():
            for query_path in query_list:
                query_info = {
                    "path": query_path,
                    "language": extractor,
                    "filename": Path(query_path).name
                }

                # Filter by category if specified
                if category:
                    if category.lower() in query_path.lower():
                        queries.append(query_info)
                else:
                    queries.append(query_info)

        return queries

    except Exception as e:
        return [f"Error: {str(e)}"]


@mcp.tool()
async def find_security_queries(language: str = None, vulnerability_type: str = None, db_path: str = None) -> dict:
    """Finds security queries by language or database path and vulnerability type using dynamic discovery"""
    try:
        # If db_path provided, get language from database
        if db_path and not language:
            db_info = await get_database_info(db_path)
            if "error" in db_info:
                return db_info
            language = db_info.get("language")
            if not language:
                return {"error": "Could not determine language from database"}

        if not language:
            return {"error": "Either language or db_path must be specified"}

        # Get all queries for the language
        all_queries = await discover_queries(language=language, category="security")

        if isinstance(all_queries, list) and len(all_queries) > 0 and isinstance(all_queries[0], str) and all_queries[0].startswith("Error"):
            return {"error": all_queries[0]}

        # Group by vulnerability types
        security_queries = {}

        vuln_patterns = {
            "sql_injection": ["sql", "injection", "sqli", "cwe-089"],
            "xss": ["xss", "cross-site", "scripting", "cwe-079"],
            "command_injection": ["command", "injection", "exec", "cwe-078"],
            "path_traversal": ["path", "traversal", "directory", "cwe-022"],
            "hardcoded_credentials": ["hardcoded", "credentials", "password", "cwe-798"],
            "csrf": ["csrf", "cross-site", "request", "forgery", "cwe-352"],
            "deserialization": ["deserialization", "pickle", "unmarshal", "cwe-502"],
            "xxe": ["xxe", "xml", "external", "entity", "cwe-611"],
            "ldap_injection": ["ldap", "injection", "cwe-090"],
            "code_injection": ["code", "injection", "eval", "cwe-094"],
            "buffer_overflow": ["buffer", "overflow", "bounds", "cwe-119", "cwe-120"],
            "use_after_free": ["use", "after", "free", "cwe-416"],
            "null_pointer": ["null", "pointer", "dereference", "cwe-476"],
            "integer_overflow": ["integer", "overflow", "cwe-190"],
            "weak_crypto": ["crypto", "cryptography", "weak", "md5", "sha1", "cwe-327"],
            "insecure_random": ["random", "insecure", "predictable", "cwe-338"]
        }

        for query in all_queries:
            if isinstance(query, dict):
                query_path = query.get("path", "").lower()
                query_name = query.get("filename", "").lower()

                for vuln_type, patterns in vuln_patterns.items():
                    if vulnerability_type and vulnerability_type.lower() != vuln_type:
                        continue

                    if any(pattern in query_path or pattern in query_name for pattern in patterns):
                        if vuln_type not in security_queries:
                            security_queries[vuln_type] = []
                        security_queries[vuln_type].append(query)

        return security_queries

    except Exception as e:
        return {"error": f"Error finding security queries: {str(e)}"}


# Removed get_common_security_queries - use find_security_queries instead


@mcp.tool()
async def analyze_database(db_path: str, query_or_suite: str, output_format: str = "sarif-latest",
                          output_path: str = "/tmp/analysis") -> str:
    """Analyzes a CodeQL database with specified query or query suite. Wrapper for 'codeql database analyze'"""
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


@mcp.tool()
async def get_database_info(db_path: str) -> dict:
    """Gets metadata about a CodeQL database including its language"""
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

        # Parse the output to extract language
        info = {
            "path": db_path_str,
            "language": None
        }

        # The output format is typically: "language: <lang>" or similar
        for line in result.stdout.split('\n'):
            line = line.strip()
            if line:
                # Try to extract language from the output
                if 'language' in line.lower() or ':' in line:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()
                        if 'language' in key:
                            info['language'] = value
                        else:
                            info[parts[0].strip()] = value
                elif not info['language']:
                    # Sometimes the output is just the language name
                    info['language'] = line

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


@mcp.tool()
async def run_security_scan(db_path: str, language: str = None, output_path: str = "/tmp/security-scan") -> str:
    """Runs a comprehensive security scan using standard security queries. Auto-detects language if not specified"""
    try:
        # Auto-detect language if not provided
        if not language:
            db_info = await get_database_info(db_path)
            if "error" in db_info:
                return db_info["error"]
            language = db_info.get("language")
            if not language:
                return "Could not determine language from database"

        # Get the appropriate security suite for the language
        query_packs = await list_query_packs()

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


if __name__ == "__main__":
    print("Starting CodeQL MCP server...")
    mcp.settings.port = os.environ.get("PORT", 8000)
    mcp.run("streamable-http")
